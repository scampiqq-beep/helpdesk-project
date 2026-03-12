from __future__ import annotations

from collections import Counter
from typing import Any

from flask import abort, flash, redirect, render_template, url_for
from sqlalchemy import or_

from helpdesk_app.models.base import db
from helpdesk_app.models.tickets import SupportTicket
from helpdesk_app.models.users import User
from helpdesk_app.services.admin_service import AdminService
from helpdesk_app.services.sla_service import SLAService


class OrganizationService:
    @staticmethod
    def _normalize_inn(value: str | None) -> str:
        return ''.join(ch for ch in str(value or '') if ch.isdigit())

    @classmethod
    def _pick_primary_name(cls, tickets: list[SupportTicket], confirmed_users: list[User], suggested_users: list[User]) -> str:
        names: Counter[str] = Counter()
        for user in confirmed_users:
            if (user.organization or '').strip():
                names[(user.organization or '').strip()] += 3
        for ticket in tickets:
            if (ticket.organization or '').strip():
                names[(ticket.organization or '').strip()] += 2
        for user in suggested_users:
            if (user.suggested_organization or '').strip():
                names[(user.suggested_organization or '').strip()] += 1
        return names.most_common(1)[0][0] if names else 'Организация не указана'

    @classmethod
    def _build_sla_summary(cls, tickets: list[SupportTicket]) -> dict[str, Any]:
        if not tickets:
            return {
                'first_response_ok': 0,
                'first_response_overdue': 0,
                'resolve_ok': 0,
                'resolve_overdue': 0,
                'active_overdue': 0,
                'compliance_percent': 0,
            }
        views = SLAService.build_ticket_views(tickets)
        first_ok = first_overdue = resolve_ok = resolve_overdue = active_overdue = 0
        for ticket in tickets:
            view = views.get(ticket.id) or {}
            first = view.get('first_response') or {}
            resolve = view.get('resolve') or {}
            if first.get('status') == 'ok':
                first_ok += 1
            elif first.get('status') == 'overdue':
                first_overdue += 1
            if resolve.get('status') == 'ok':
                resolve_ok += 1
            elif resolve.get('status') == 'overdue':
                resolve_overdue += 1
            if view.get('summary_status') == 'overdue' and not SLAService.ticket_closed_at_value(ticket):
                active_overdue += 1
        total_closed_checks = resolve_ok + resolve_overdue
        compliance_percent = round((resolve_ok / total_closed_checks) * 100) if total_closed_checks else 0
        return {
            'first_response_ok': first_ok,
            'first_response_overdue': first_overdue,
            'resolve_ok': resolve_ok,
            'resolve_overdue': resolve_overdue,
            'active_overdue': active_overdue,
            'compliance_percent': compliance_percent,
        }

    @classmethod
    def build_context(cls, inn: str) -> dict[str, Any]:
        AdminService.ensure_admin_or_operator()
        inn = cls._normalize_inn(inn)
        if not inn:
            abort(404)

        tickets = (
            SupportTicket.query
            .filter(SupportTicket.inn == inn)
            .order_by(SupportTicket.created_at.desc())
            .all()
        )
        confirmed_users = (
            User.query
            .filter(User.role == 'client', User.inn == inn)
            .order_by(User.last_name.asc(), User.name.asc(), User.email.asc())
            .all()
        )
        suggested_users = (
            User.query
            .filter(
                User.role == 'client',
                User.suggested_inn == inn,
                or_(User.inn.is_(None), User.inn != inn),
            )
            .order_by(User.last_name.asc(), User.name.asc(), User.email.asc())
            .all()
        )

        if not tickets and not confirmed_users and not suggested_users:
            abort(404)

        primary_name = cls._pick_primary_name(tickets, confirmed_users, suggested_users)
        addresses = []
        seen_addresses: set[str] = set()
        for raw in [*(u.address for u in confirmed_users), *(u.suggested_address for u in suggested_users), *(t.address for t in tickets)]:
            val = (raw or '').strip()
            if val and val not in seen_addresses:
                seen_addresses.add(val)
                addresses.append(val)

        contacts = []
        seen_contacts: set[tuple[str, str, str]] = set()
        for user, source in [*((u, 'confirmed') for u in confirmed_users), *((u, 'suggested') for u in suggested_users)]:
            fio = ' '.join(part for part in [user.last_name, user.name, user.patronymic] if (part or '').strip()).strip() or user.username
            key = (fio, (user.email or '').strip().lower(), (user.phone or '').strip())
            if key in seen_contacts:
                continue
            seen_contacts.add(key)
            contacts.append({
                'fio': fio,
                'email': user.email,
                'phone': user.phone,
                'position': user.position,
                'source': source,
                'organization': user.organization if source == 'confirmed' else user.suggested_organization,
                'address': user.address if source == 'confirmed' else user.suggested_address,
                'user': user,
            })

        open_statuses = {'Новая', 'Принята', 'В работе', 'Ожидание', 'Ожидание клиента'}
        total_tickets = len(tickets)
        open_tickets = sum(1 for t in tickets if (t.status or '').strip() in open_statuses)
        closed_tickets = total_tickets - open_tickets
        internal_notes = [t for t in tickets if (t.internal_comment or '').strip()][:10]
        ticket_history = tickets[:20]
        sla_summary = cls._build_sla_summary(tickets)

        return {
            'inn': inn,
            'organization_name': primary_name,
            'confirmed_users': confirmed_users,
            'suggested_users': suggested_users,
            'contacts': contacts,
            'addresses': addresses,
            'tickets': tickets,
            'ticket_history': ticket_history,
            'internal_notes': internal_notes,
            'stats': {
                'total_tickets': total_tickets,
                'open_tickets': open_tickets,
                'closed_tickets': closed_tickets,
                'contacts_count': len(contacts),
                'confirmed_count': len(confirmed_users),
                'suggested_count': len(suggested_users),
            },
            'sla_summary': sla_summary,
        }



    @staticmethod
    def _normalize_org_key(value: str | None) -> str:
        return ' '.join(str(value or '').strip().lower().split())



    @classmethod
    def _find_entities_for_key(cls, key: str) -> tuple[list[User], list[SupportTicket]]:
        key = (key or '').strip()
        if not key:
            return [], []
        users = User.query.filter(User.role == 'client').all()
        tickets = (
            SupportTicket.query
            .filter(or_(SupportTicket.organization.isnot(None), SupportTicket.inn.isnot(None)))
            .all()
        )

        matched_users: list[User] = []
        for user in users:
            org_name = (user.organization or user.suggested_organization or '').strip()
            inn = cls._normalize_inn(user.inn or user.suggested_inn)
            user_key = f'inn:{inn}' if inn else f'name:{cls._normalize_org_key(org_name)}'
            if user_key == key:
                matched_users.append(user)

        matched_tickets: list[SupportTicket] = []
        for ticket in tickets:
            org_name = (ticket.organization or '').strip()
            inn = cls._normalize_inn(ticket.inn)
            ticket_key = f'inn:{inn}' if inn else f'name:{cls._normalize_org_key(org_name)}'
            if ticket_key == key:
                matched_tickets.append(ticket)

        return matched_users, matched_tickets

    @classmethod
    def update_organization(cls, key: str, name: str | None, inn: str | None, address: str | None) -> None:
        AdminService.ensure_admin_or_operator()
        users, tickets = cls._find_entities_for_key(key)
        if not users and not tickets:
            flash('Организация не найдена.', 'warning')
            return

        name = (name or '').strip()
        inn = cls._normalize_inn(inn)
        address = (address or '').strip()

        for user in users:
            if user.organization is not None:
                user.organization = name or None
            if user.suggested_organization is not None:
                user.suggested_organization = name or None
            if user.inn is not None or inn:
                user.inn = inn or None
            if user.suggested_inn is not None:
                user.suggested_inn = inn or None
            if user.address is not None or address:
                user.address = address or None
            if user.suggested_address is not None:
                user.suggested_address = address or None

        for ticket in tickets:
            ticket.organization = name or None
            ticket.inn = inn or None
            ticket.address = address or None

        db.session.commit()
        flash('Организация обновлена.', 'success')

    @classmethod
    def delete_organization(cls, key: str) -> None:
        AdminService.ensure_admin_or_operator()
        users, tickets = cls._find_entities_for_key(key)
        if not users and not tickets:
            flash('Организация не найдена.', 'warning')
            return

        for user in users:
            user.organization = None
            user.inn = None
            user.address = None
            if user.suggested_organization is not None:
                user.suggested_organization = None
            if user.suggested_inn is not None:
                user.suggested_inn = None
            if user.suggested_address is not None:
                user.suggested_address = None

        for ticket in tickets:
            ticket.organization = None
            ticket.inn = None
            ticket.address = None

        db.session.commit()
        flash('Организация удалена из реестра. Реквизиты очищены в связанных карточках и заявках.', 'success')

    @classmethod
    def handle_list_post(cls, form):
        action = (form.get('action') or '').strip()
        key = (form.get('key') or '').strip()
        if action == 'edit':
            cls.update_organization(
                key=key,
                name=form.get('name'),
                inn=form.get('inn'),
                address=form.get('address'),
            )
        elif action == 'delete':
            cls.delete_organization(key)
        else:
            flash('Неизвестное действие.', 'warning')
        q = (form.get('q') or '').strip()
        return redirect(url_for('admin_organizations', q=q or None))

    @classmethod
    def build_list_context(cls, query: str | None = None) -> dict[str, Any]:
        AdminService.ensure_admin_or_operator()
        query = (query or '').strip()

        users = (
            User.query
            .filter(User.role == 'client')
            .order_by(User.created_at.desc())
            .all()
        )
        tickets = (
            SupportTicket.query
            .filter(or_(SupportTicket.organization.isnot(None), SupportTicket.inn.isnot(None)))
            .order_by(SupportTicket.created_at.desc())
            .all()
        )

        registry: dict[str, dict[str, Any]] = {}

        def ensure_entry(key: str) -> dict[str, Any]:
            return registry.setdefault(key, {
                'name_votes': Counter(),
                'inn': '',
                'addresses': Counter(),
                'users_count': 0,
                'tickets_count': 0,
                'open_tickets_count': 0,
                'last_activity': None,
                'source_count': 0,
            })

        def touch_activity(entry: dict[str, Any], dt):
            if dt and (entry['last_activity'] is None or dt > entry['last_activity']):
                entry['last_activity'] = dt

        open_statuses = {'Новая', 'Принята', 'В работе', 'Ожидание', 'Ожидание клиента'}

        for user in users:
            org_name = (user.organization or user.suggested_organization or '').strip()
            inn = cls._normalize_inn(user.inn or user.suggested_inn)
            address = (user.address or user.suggested_address or '').strip()
            key = f'inn:{inn}' if inn else f'name:{cls._normalize_org_key(org_name)}'
            if key in {'name:', 'name:организация не указана'}:
                continue
            entry = ensure_entry(key)
            if org_name:
                entry['name_votes'][org_name] += 3 if user.organization else 1
            if inn and not entry['inn']:
                entry['inn'] = inn
            if address:
                entry['addresses'][address] += 1
            entry['users_count'] += 1
            entry['source_count'] += 1
            touch_activity(entry, user.created_at)

        for ticket in tickets:
            org_name = (ticket.organization or '').strip()
            inn = cls._normalize_inn(ticket.inn)
            address = (ticket.address or '').strip()
            key = f'inn:{inn}' if inn else f'name:{cls._normalize_org_key(org_name)}'
            if key == 'name:':
                continue
            entry = ensure_entry(key)
            if org_name:
                entry['name_votes'][org_name] += 2
            if inn and not entry['inn']:
                entry['inn'] = inn
            if address:
                entry['addresses'][address] += 1
            entry['tickets_count'] += 1
            if (ticket.status or '').strip() in open_statuses:
                entry['open_tickets_count'] += 1
            entry['source_count'] += 1
            touch_activity(entry, ticket.created_at)

        items = []
        for key, entry in registry.items():
            primary_name = entry['name_votes'].most_common(1)[0][0] if entry['name_votes'] else 'Организация не указана'
            address = entry['addresses'].most_common(1)[0][0] if entry['addresses'] else ''
            row = {
                'key': key,
                'name': primary_name,
                'inn': entry['inn'],
                'address': address,
                'users_count': entry['users_count'],
                'tickets_count': entry['tickets_count'],
                'open_tickets_count': entry['open_tickets_count'],
                'last_activity': entry['last_activity'],
                'has_card': bool(entry['inn']),
            }
            haystack = ' '.join([row['name'], row['inn'], row['address']]).lower()
            if query and query.lower() not in haystack:
                continue
            items.append(row)

        items.sort(key=lambda x: ((x['last_activity'] is None), -(x['last_activity'].timestamp() if x['last_activity'] else 0), x['name'].lower()))
        return {
            'organizations': items,
            'q': query,
            'organizations_count': len(items),
        }

    @classmethod
    def render_list(cls, query: str | None = None):
        return render_template('admin_organizations.html', **cls.build_list_context(query=query))

    @classmethod
    def render_card(cls, inn: str):
        return render_template('admin_organization_card.html', **cls.build_context(inn))
