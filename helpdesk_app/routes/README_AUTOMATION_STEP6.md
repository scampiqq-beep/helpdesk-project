# Automation Engine — Step 6 (Preview + admin import fix)

Этот шаг:
- исправляет ImportError по `AdminAccessDenied` из `helpdesk_app.services`
- добавляет preview-layer для правил автоматизации
- подготавливает UI/audit к показу результата срабатывания правил

Что входит:
- compatibility exports в services.__init__
- preview service
- безопасный payload для страницы/модалки preview
