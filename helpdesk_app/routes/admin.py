from __future__ import annotations

from flask import request
from flask_login import login_required

from helpdesk_app.services import AdminAccessDenied, AdminService, AdminSettingsService, AdminSLACalendarService
from flask import redirect, url_for


@login_required
def admin_dashboard():
    try:
        return AdminService.render_dashboard()
    except AdminAccessDenied:
        return AdminService.deny_response()


@login_required
def admin_charts():
    try:
        return AdminService.render_charts()
    except AdminAccessDenied:
        return AdminService.deny_response()


@login_required
def admin_audit():
    try:
        return AdminService.render_audit()
    except AdminAccessDenied:
        return AdminService.deny_response()


@login_required
def admin_support_list():
    from helpdesk_app.routes.tickets import ticket_list
    return ticket_list()


@login_required
def admin_users():
    try:
        if request.method == 'GET':
            return AdminService.render_users_page()
        handled = AdminService.handle_users_post()
        if handled is not None:
            return handled
        return AdminService.call_legacy('admin_users')
    except AdminAccessDenied:
        return AdminService.deny_response()
    except Exception:
        return AdminService.call_legacy('admin_users')


@login_required
def admin_settings():
    try:
        AdminService.ensure_admin()
    except AdminAccessDenied:
        return AdminService.deny_response()
    section = AdminSettingsService.normalize_section(request.args.get('tab') or 'bitrix')
    if request.method == 'POST':
        handled = AdminSettingsService.handle_post()
        if handled is not None:
            return handled
    return AdminSettingsService.render_page(section)


@login_required
def admin_settings_section(section):
    try:
        AdminService.ensure_admin()
    except AdminAccessDenied:
        return AdminService.deny_response()
    section = AdminSettingsService.normalize_section(section)
    if request.method == 'POST':
        handled = AdminSettingsService.handle_post()
        if handled is not None:
            return handled
    return AdminSettingsService.render_page(section)


@login_required
def admin_sla_calendar():
    return redirect(url_for('admin_sla_settings'))


@login_required
def admin_sla_settings():
    try:
        AdminService.ensure_admin()
    except AdminAccessDenied:
        return AdminService.deny_response()
    if request.method == 'POST':
        handled = AdminSLACalendarService.handle_post(page='sla')
        if handled is not None:
            return handled
    return AdminSLACalendarService.render_page(page='sla')


@login_required
def admin_work_calendar():
    try:
        AdminService.ensure_admin()
    except AdminAccessDenied:
        return AdminService.deny_response()
    if request.method == 'POST':
        handled = AdminSLACalendarService.handle_post(page='calendar')
        if handled is not None:
            return handled
    return AdminSLACalendarService.render_page(page='calendar')


@login_required
def admin_user_edit(user_id):
    try:
        AdminService.ensure_admin_or_operator()
    except AdminAccessDenied:
        return AdminService.deny_response()
    return AdminService.call_legacy('admin_user_edit', user_id)


@login_required
def admin_user_reset_password(user_id):
    try:
        AdminService.ensure_admin()
    except AdminAccessDenied:
        return AdminService.deny_response()
    return AdminService.call_legacy('admin_reset_password', user_id)


@login_required
def admin_delete_operator(user_id):
    try:
        AdminService.ensure_admin()
    except AdminAccessDenied:
        return AdminService.deny_response()
    return AdminService.call_legacy('admin_delete_operator', user_id)


@login_required
def admin_edit_enduser(user_id):
    try:
        AdminService.ensure_admin()
    except AdminAccessDenied:
        return AdminService.deny_response()
    return AdminService.call_legacy('admin_edit_enduser', user_id)


EXTRACTED_ENDPOINTS = {
    'admin': admin_dashboard,
    'admin_dashboard': admin_dashboard,
    'admin_charts': admin_charts,
    'admin_audit': admin_audit,
    'admin_support_list': admin_support_list,
    'admin_users': admin_users,
    'admin_settings': admin_settings,
    'admin_settings_section': admin_settings_section,
    'admin_sla_calendar': admin_sla_calendar,
    'admin_sla_settings': admin_sla_settings,
    'admin_work_calendar': admin_work_calendar,
    'admin_user_edit': admin_user_edit,
    'admin_user_reset_password': admin_user_reset_password,
    'admin_delete_operator': admin_delete_operator,
    'admin_edit_enduser': admin_edit_enduser,
}
