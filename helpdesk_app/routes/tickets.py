from __future__ import annotations

from flask import Blueprint, flash, jsonify, redirect, request, url_for
from flask_login import current_user, login_required
from helpdesk_app.models.users import User

from helpdesk_app.services import (
    KanbanService,
    PermissionDenied,
    TicketDetailService,
    TicketListService,
    TicketService,
    ValidationError,
)

bp = Blueprint('tickets_bp', __name__)


@login_required
def api_user_tickets():
    from helpdesk_app.runtime import get_runtime

    if isinstance(current_user, User):
        return jsonify([])

    tickets = TicketService.get_user_tickets(current_user.id)
    return jsonify([TicketService.serialize_user_ticket(t) for t in tickets])


@login_required
def create_ticket():
    from helpdesk_app.runtime import get_runtime
    legacy = get_runtime()
    return legacy.create_ticket()


@login_required
def ticket_list():
    from helpdesk_app.runtime import get_runtime
    legacy = get_runtime()
    try:
        return TicketListService.render_page(current_user)
    except Exception:
        return legacy.ticket_list()


@login_required
def ticket_detail(ticket_id: int):
    from helpdesk_app.runtime import get_runtime
    legacy = get_runtime()

    if request.method == 'GET':
        try:
            return TicketDetailService.render_page(
                ticket_id,
                current_user,
                org_mismatch_requested=bool(request.args.get('org_mismatch')),
            )
        except PermissionDenied as exc:
            flash(str(exc), 'error')
            return redirect(url_for('ticket_list'))
        except Exception:
            return legacy.ticket_detail(ticket_id)

    action = (request.form.get('action') or '').strip()
    try:
        if action == 'copy_org_to_profile':
            TicketService.copy_org_to_profile(ticket_id, current_user)
            flash('Реквизиты перенесены в профиль.', 'success')
            return redirect(url_for('ticket_detail', ticket_id=ticket_id))

        if action == 'finish_modal':
            result = TicketService.finish_modal(
                ticket_id=ticket_id,
                actor=current_user,
                finish_choice=request.form.get('finish_choice'),
                finish_comment=request.form.get('finish_comment'),
            )
            if result.get('status') == 'Ожидание':
                flash("Заявка переведена в состояние 'Ожидание'", 'success')
            else:
                flash('Заявка завершена', 'success')
            return redirect(url_for('ticket_detail', ticket_id=ticket_id))

        if action in {'accept_work', 'request_rework'}:
            result = TicketService.apply_client_feedback(
                ticket_id=ticket_id,
                actor=current_user,
                action=action,
                comment_text=request.form.get('comment') or request.form.get('rework_comment') or '',
            )
            if result.get('status') == 'Завершена':
                flash('Спасибо за подтверждение! Заявка завершена.', 'success')
            else:
                flash('Заявка возвращена в работу.', 'success')
            return redirect(url_for('ticket_detail', ticket_id=ticket_id))

        if action == 'reopen_ticket_operator':
            TicketService.reopen_ticket(ticket_id=ticket_id, actor=current_user, operator_mode=True)
            flash('Заявка возобновлена', 'success')
            return redirect(url_for('ticket_detail', ticket_id=ticket_id))

        if action == 'reopen_ticket':
            TicketService.reopen_ticket(ticket_id=ticket_id, actor=current_user, operator_mode=False)
            flash('Заявка возобновлена', 'success')
            return redirect(url_for('ticket_detail', ticket_id=ticket_id))

        if action == 'client_complete_ticket':
            TicketService.client_complete_ticket(ticket_id=ticket_id, actor=current_user)
            flash('Заявка успешно завершена.', 'success')
            return redirect(url_for('ticket_detail', ticket_id=ticket_id))

        if action == 'update_ticket_meta':
            TicketService.update_meta(
                ticket_id=ticket_id,
                actor=current_user,
                new_status=request.form.get('status'),
                new_priority=request.form.get('priority'),
                new_category_id=request.form.get('category_id'),
                tag_ids=request.form.getlist('tag_ids'),
            )
            flash('Поля заявки обновлены', 'success')
            return redirect(url_for('ticket_detail', ticket_id=ticket_id))

        if action in {'mark_spam', 'close_mistake', 'close_withdrawn', 'close_duplicate'}:
            TicketService.close_ticket_as(ticket_id=ticket_id, actor=current_user, reason_code=action)
            action_messages = {
                'mark_spam': 'Заявка закрыта как Спам',
                'close_mistake': 'Заявка закрыта как ошибочная',
                'close_withdrawn': 'Заявка закрыта по отказу клиента',
                'close_duplicate': 'Заявка закрыта как Дубликат',
            }
            flash(action_messages[action], 'warning')
            return redirect(url_for('ticket_detail', ticket_id=ticket_id))

        if action == 'complete_ticket':
            TicketService.send_to_client_confirmation(ticket_id=ticket_id, actor=current_user)
            flash('Заявка отправлена клиенту на подтверждение. Клиент должен подтвердить решение в течение 24 часов.', 'success')
            return redirect(url_for('ticket_detail', ticket_id=ticket_id))

        if action == 'delegate_ticket':
            department_ids = request.form.getlist('department_ids')
            if not department_ids:
                single_id = request.form.get('department_id')
                if single_id:
                    department_ids = [single_id]
            result = TicketService.delegate_ticket(
                ticket_id=ticket_id,
                actor=current_user,
                department_ids=department_ids,
                change_status=request.form.get('change_status') == 'on',
            )
            extra = result.get('shared_departments') or []
            if extra:
                flash(
                    'Заявка делегирована: основной отдел — ' + result['main_department'].name + '; доп. отделы — ' + ', '.join(d.name for d in extra),
                    'success'
                )
            else:
                flash(f"Заявка делегирована в отдел: {result['main_department'].name}", 'success')
            return redirect(url_for('ticket_detail', ticket_id=ticket_id))

        if action == 'update_shared_departments':
            TicketService.update_shared_departments(
                ticket_id=ticket_id,
                actor=current_user,
                department_ids=request.form.getlist('shared_department_ids'),
            )
            flash('Дополнительные отделы обновлены', 'success')
            return redirect(url_for('ticket_detail', ticket_id=ticket_id))

        if action == 'update_departments_sidebar':
            TicketService.update_departments_sidebar(
                ticket_id=ticket_id,
                actor=current_user,
                new_main_id=request.form.get('department_id'),
                shared_ids=request.form.getlist('shared_department_ids'),
            )
            flash('Отделы заявки обновлены', 'success')
            return redirect(url_for('ticket_detail', ticket_id=ticket_id))

        is_comment_submit = (not action) and (
            bool((request.form.get('message') or '').strip()) or
            bool([f for f in request.files.getlist('files') if getattr(f, 'filename', '') and str(f.filename).strip()])
        )
        if is_comment_submit:
            TicketService.add_comment(
                ticket_id=ticket_id,
                actor=current_user,
                message_text=request.form.get('message'),
                uploaded_files=request.files.getlist('files'),
            )
            flash('Комментарий добавлен', 'success')
            return redirect(url_for('ticket_detail', ticket_id=ticket_id))
    except PermissionDenied as exc:
        flash(str(exc), 'error')
        return redirect(url_for('ticket_detail', ticket_id=ticket_id))
    except ValidationError as exc:
        flash(str(exc), 'error')
        return redirect(url_for('ticket_detail', ticket_id=ticket_id))
    except Exception as exc:
        legacy.db.session.rollback()
        flash(f'Не удалось обработать действие по заявке: {exc}', 'error')
        return redirect(url_for('ticket_detail', ticket_id=ticket_id))

    return legacy.ticket_detail(ticket_id)


@login_required
def kanban():
    from helpdesk_app.runtime import get_runtime
    legacy = get_runtime()
    try:
        return KanbanService.render_page(current_user)
    except PermissionDenied as exc:
        flash(str(exc), 'error')
        return redirect(url_for('ticket_list'))
    except Exception:
        return legacy.kanban()


@login_required
def api_kanban_tickets():
    from helpdesk_app.runtime import get_runtime
    legacy = get_runtime()
    try:
        return KanbanService.render_data(current_user)
    except Exception:
        return legacy.api_kanban_tickets()


@login_required
def accept_ticket(ticket_id: int):
    try:
        ticket = TicketService.accept_ticket(ticket_id, current_user)
        flash('Заявка принята в работу', 'success')
        return redirect(url_for('ticket_detail', ticket_id=ticket.id))
    except PermissionDenied as exc:
        flash(str(exc), 'error')
        return redirect(url_for('ticket_detail', ticket_id=ticket_id))
    except Exception as exc:
        from helpdesk_app.runtime import get_runtime
        legacy = get_runtime()
        legacy.db.session.rollback()
        flash(f'Не удалось взять заявку в работу: {exc}', 'error')
        return redirect(url_for('ticket_detail', ticket_id=ticket_id))


@login_required
def edit_ticket_comment(ticket_id: int, message_id: int):
    try:
        result = TicketService.edit_comment(
            ticket_id=ticket_id,
            message_id=message_id,
            actor=current_user,
            new_text=request.form.get('message') or '',
            delete_attachment_ids=request.form.getlist('delete_attachment_ids'),
        )
        flash('Комментарий обновлён', 'success')
        return redirect(url_for('ticket_detail', ticket_id=result['ticket'].id, _anchor=f'comment-{message_id}'))
    except PermissionDenied as exc:
        flash(str(exc), 'error')
        return redirect(url_for('ticket_detail', ticket_id=ticket_id))
    except ValidationError as exc:
        flash(str(exc), 'error')
        return redirect(url_for('ticket_detail', ticket_id=ticket_id, _anchor=f'comment-{message_id}'))
    except Exception as exc:
        from helpdesk_app.runtime import get_runtime
        legacy = get_runtime()
        legacy.db.session.rollback()
        flash(f'Не удалось обновить комментарий: {exc}', 'error')
        return redirect(url_for('ticket_detail', ticket_id=ticket_id, _anchor=f'comment-{message_id}'))


@login_required
def delete_ticket_comment(ticket_id: int, message_id: int):
    try:
        result = TicketService.delete_comment(ticket_id, message_id, current_user)
        flash('Комментарий удалён', 'success')
        return redirect(url_for('ticket_detail', ticket_id=result['ticket'].id))
    except PermissionDenied as exc:
        flash(str(exc), 'error')
        return redirect(url_for('ticket_detail', ticket_id=ticket_id))
    except ValidationError as exc:
        flash(str(exc), 'error')
        return redirect(url_for('ticket_detail', ticket_id=ticket_id))
    except Exception as exc:
        from helpdesk_app.runtime import get_runtime
        legacy = get_runtime()
        legacy.db.session.rollback()
        flash(f'Не удалось удалить комментарий: {exc}', 'error')
        return redirect(url_for('ticket_detail', ticket_id=ticket_id))




@login_required
def save_ticket_list_preferences():
    payload = request.get_json(silent=True) or {}
    try:
        compact = payload.get('compact')
        if compact is not None:
            compact = bool(compact)
        show = payload.get('show')
        try:
            show = int(show) if show is not None else None
        except (TypeError, ValueError):
            show = None
        state = TicketListService.save_preferences(current_user, compact=compact, show=show)
        return jsonify({'success': True, 'state': state})
    except Exception as exc:
        from helpdesk_app.runtime import get_runtime
        legacy = get_runtime()
        legacy.db.session.rollback()
        return jsonify({'success': False, 'error': str(exc)}), 500

@login_required
def update_ticket_department(ticket_id: int):
    payload = request.get_json(silent=True) or {}
    try:
        result = TicketService.update_department(
            ticket_id=ticket_id,
            actor=current_user,
            department_name=payload.get('department'),
        )
        return jsonify({
            'success': True,
            'department': result['department'],
            'status': result['status'],
        })
    except PermissionDenied as exc:
        return jsonify({'success': False, 'error': str(exc)}), 403
    except ValidationError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400
    except Exception as exc:
        from helpdesk_app.runtime import get_runtime
        legacy = get_runtime()
        legacy.db.session.rollback()
        return jsonify({'success': False, 'error': str(exc)}), 500


@login_required
def update_ticket_priority(ticket_id: int):
    payload = request.get_json(silent=True) or {}
    try:
        result = TicketService.update_priority(
            ticket_id=ticket_id,
            actor=current_user,
            priority_value=payload.get('priority'),
        )
        return jsonify({
            'success': True,
            'priority': result['priority'],
            'priority_display': result['priority_display'],
        })
    except PermissionDenied as exc:
        return jsonify({'success': False, 'error': str(exc)}), 403
    except ValidationError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400
    except Exception as exc:
        from helpdesk_app.runtime import get_runtime
        legacy = get_runtime()
        legacy.db.session.rollback()
        return jsonify({'success': False, 'error': str(exc)}), 500


@login_required
def toggle_ticket_critical(ticket_id: int):
    try:
        result = TicketService.toggle_critical(ticket_id=ticket_id, actor=current_user)
        return jsonify({'success': True, **result})
    except PermissionDenied as exc:
        return jsonify({'success': False, 'message': str(exc)}), 403
    except Exception as exc:
        from helpdesk_app.runtime import get_runtime
        legacy = get_runtime()
        legacy.db.session.rollback()
        return jsonify({'success': False, 'message': str(exc)}), 500


EXTRACTED_ENDPOINTS = {
    'api_user_tickets': api_user_tickets,
    'create_ticket': create_ticket,
    'ticket_list': ticket_list,
    'ticket_detail': ticket_detail,
    'kanban': kanban,
    'admin_kanban': kanban,
    'api_kanban_tickets': api_kanban_tickets,
    'accept_ticket': accept_ticket,
    'edit_ticket_comment': edit_ticket_comment,
    'delete_ticket_comment': delete_ticket_comment,
    'update_ticket_department': update_ticket_department,
    'update_ticket_priority': update_ticket_priority,
    'toggle_ticket_critical': toggle_ticket_critical,
    'save_ticket_list_preferences': save_ticket_list_preferences,
}
