# Automation Engine — Step 4 (Runtime rules + import fix)

Этот шаг:
- исправляет ImportError по ticket_service
- подключает правила из instance/automation_rules.json в runtime
- сохраняет совместимость со старым импортом services.__init__

Что входит:
- ticket_service bridge с исключениями совместимости
- runtime loader для admin-created automation rules
- обновлённый automation runtime service
