from __future__ import annotations

from flask import redirect, url_for
from flask_login import login_required

from helpdesk_app.services.admin_directory_service import AdminDirectoryService
from helpdesk_app.services.admin_service import AdminAccessDenied, AdminService
from helpdesk_app.services.knowledge_service import KnowledgeService


@login_required
def knowledge():
    return KnowledgeService.render_index()


@login_required
def kb_article(article_id: int):
    return KnowledgeService.render_article(article_id)


@login_required
def kb_favorites():
    return redirect(url_for('knowledge', fav='1'))


@login_required
def api_kb_templates():
    return KnowledgeService.api_templates()


@login_required
def api_kb_toggle_favorite(article_id: int):
    return KnowledgeService.toggle_favorite(article_id)


@login_required
def kb_manage():
    try:
        return KnowledgeService.render_manage()
    except AdminAccessDenied:
        return AdminService.deny_response()


@login_required
def kb_category_add():
    try:
        return KnowledgeService.add_category()
    except AdminAccessDenied:
        return AdminService.deny_response()


@login_required
def kb_category_edit(category_id: int):
    try:
        return KnowledgeService.edit_category(category_id)
    except AdminAccessDenied:
        return AdminService.deny_response()


@login_required
def kb_category_delete(category_id: int):
    try:
        return KnowledgeService.delete_category(category_id)
    except AdminAccessDenied:
        return AdminService.deny_response()


@login_required
def kb_article_add():
    try:
        return KnowledgeService.add_article()
    except AdminAccessDenied:
        return AdminService.deny_response()


@login_required
def kb_article_edit(article_id: int):
    try:
        return KnowledgeService.edit_article(article_id)
    except AdminAccessDenied:
        return AdminService.deny_response()


@login_required
def kb_article_delete(article_id: int):
    try:
        return KnowledgeService.delete_article(article_id)
    except AdminAccessDenied:
        return AdminService.deny_response()


@login_required
def add_faq():
    try:
        return KnowledgeService.add_faq()
    except AdminAccessDenied:
        return AdminService.deny_response()


@login_required
def edit_faq(id: int):
    try:
        return KnowledgeService.edit_faq(id)
    except AdminAccessDenied:
        return AdminService.deny_response()


@login_required
def user_knowledge_base():
    return redirect(url_for('knowledge'))


@login_required
def admin_close_reasons():
    try:
        return AdminDirectoryService.render_close_reasons()
    except AdminAccessDenied:
        return AdminService.deny_response()


@login_required
def admin_close_reason_new():
    try:
        return AdminDirectoryService.create_close_reason()
    except AdminAccessDenied:
        return AdminService.deny_response()


@login_required
def admin_close_reason_edit(reason_id: int):
    try:
        return AdminDirectoryService.edit_close_reason(reason_id)
    except AdminAccessDenied:
        return AdminService.deny_response()


@login_required
def admin_close_reason_delete(reason_id: int):
    try:
        return AdminDirectoryService.delete_close_reason(reason_id)
    except AdminAccessDenied:
        return AdminService.deny_response()


EXTRACTED_ENDPOINTS = {
    'knowledge': knowledge,
    'kb_article': kb_article,
    'kb_favorites': kb_favorites,
    'api_kb_templates': api_kb_templates,
    'api_kb_toggle_favorite': api_kb_toggle_favorite,
    'kb_manage': kb_manage,
    'kb_category_add': kb_category_add,
    'kb_category_edit': kb_category_edit,
    'kb_category_delete': kb_category_delete,
    'kb_article_add': kb_article_add,
    'kb_article_edit': kb_article_edit,
    'kb_article_delete': kb_article_delete,
    'add_faq': add_faq,
    'edit_faq': edit_faq,
    'user_knowledge_base': user_knowledge_base,
    'admin_close_reasons': admin_close_reasons,
    'admin_close_reason_new': admin_close_reason_new,
    'admin_close_reason_edit': admin_close_reason_edit,
    'admin_close_reason_delete': admin_close_reason_delete,
}
