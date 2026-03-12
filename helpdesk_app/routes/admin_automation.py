from __future__ import annotations

from flask import flash, redirect, render_template, request, url_for
from flask_login import login_required

from helpdesk_app.services.admin_automation_ui_service import AdminAutomationUIService
from helpdesk_app.services.admin_service import AdminAccessDenied, AdminService


@login_required
def admin_automation_index():
    try:
        AdminService.ensure_admin()
    except AdminAccessDenied:
        return AdminService.deny_response()
    return render_template(
        "admin_automation_rules.html",
        **AdminAutomationUIService.page_context(),
    )


@login_required
def admin_automation_create():
    try:
        AdminService.ensure_admin()
    except AdminAccessDenied:
        return AdminService.deny_response()

    payload = {
        "key": request.form.get("key", "").strip(),
        "name": request.form.get("name", "").strip(),
        "enabled": request.form.get("enabled") == "1",
        "priority": int(request.form.get("priority", "100") or 100),
        "stop_on_match": request.form.get("stop_on_match") == "1",
        "conditions": [],
        "actions": [],
    }

    cond_types = request.form.getlist("condition_type[]") or [request.form.get("condition_type", "").strip()]
    cond_values = request.form.getlist("condition_value[]") or [request.form.get("condition_value", "").strip()]
    action_types = request.form.getlist("action_type[]") or [request.form.get("action_type", "").strip()]
    action_values = request.form.getlist("action_value[]") or [request.form.get("action_value", "").strip()]

    for idx, cond_type in enumerate(cond_types):
        cond_type = (cond_type or "").strip()
        cond_value = (cond_values[idx] if idx < len(cond_values) else "")
        if cond_type:
            payload["conditions"].append({"type": cond_type, "value": (cond_value or "").strip()})

    for idx, action_type in enumerate(action_types):
        action_type = (action_type or "").strip()
        action_value = (action_values[idx] if idx < len(action_values) else "")
        if action_type:
            payload["actions"].append({"type": action_type, "value": (action_value or "").strip()})

    if not payload["key"]:
        flash("Укажите ключ правила", "danger")
        return redirect(url_for("admin_automation_index"))

    rule = AdminAutomationUIService.create_rule(payload)
    flash(f"Правило «{rule['name']}» сохранено", "success")
    return redirect(url_for("admin_automation_index"))


@login_required
def admin_automation_delete(rule_key):
    try:
        AdminService.ensure_admin()
    except AdminAccessDenied:
        return AdminService.deny_response()

    deleted = AdminAutomationUIService.delete_rule(rule_key)
    if deleted:
        flash("Правило удалено", "success")
    else:
        flash("Правило не найдено", "warning")
    return redirect(url_for("admin_automation_index"))


@login_required
def admin_automation_toggle(rule_key):
    try:
        AdminService.ensure_admin()
    except AdminAccessDenied:
        return AdminService.deny_response()

    changed = AdminAutomationUIService.toggle_rule(rule_key)
    if changed:
        flash("Статус правила изменён", "success")
    else:
        flash("Правило не найдено", "warning")
    return redirect(url_for("admin_automation_index"))


EXTRACTED_ENDPOINTS = {
    'admin_automation_index': admin_automation_index,
    'admin_automation_create': admin_automation_create,
    'admin_automation_delete': admin_automation_delete,
    'admin_automation_toggle': admin_automation_toggle,
}
