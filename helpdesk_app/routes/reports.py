from __future__ import annotations

from flask import Blueprint, redirect, request, url_for
from flask_login import login_required

from helpdesk_app.services import ReportService

bp = Blueprint('reports_bp', __name__)


@login_required
def admin_stats():
    return redirect(url_for('admin_statistics', **request.args))


@login_required
def admin_analytics():
    denied = ReportService.ensure_admin_or_redirect()
    if denied is not None:
        return denied

    period = request.args.get('period', '30')
    department_id = request.args.get('department_id', type=int)
    operator_id = request.args.get('operator_id', type=int)
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')

    return redirect(
        url_for(
            'admin_statistics',
            period=period,
            department_id=department_id or '',
            operator_id=operator_id or '',
            date_from=date_from,
            date_to=date_to,
        )
    )


@login_required
def admin_analytics_export():
    denied = ReportService.ensure_admin_or_redirect()
    if denied is not None:
        return denied
    period = request.args.get('period', '30')
    department_id = request.args.get('department_id', type=int)
    operator_id = request.args.get('operator_id', type=int)
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    return redirect(
        url_for(
            'admin_reports_export_xlsx',
            period=period,
            department_id=department_id or '',
            operator_id=operator_id or '',
            date_from=date_from,
            date_to=date_to,
        )
    )


@login_required
def admin_statistics():
    return ReportService.render_statistics()


@login_required
def admin_reports():
    return ReportService.render_reports()


@login_required
def admin_reports_legacy():
    return redirect(url_for('admin_reports', **request.args))


@login_required
def admin_reports_export_xlsx():
    return ReportService.export_xlsx()


EXTRACTED_ENDPOINTS = {
    'admin_stats': admin_stats,
    'admin_analytics': admin_analytics,
    'admin_analytics_export': admin_analytics_export,
    'admin_statistics': admin_statistics,
    'admin_reports': admin_reports,
    'admin_reports_legacy': admin_reports_legacy,
    'admin_reports_export_xlsx': admin_reports_export_xlsx,
}
