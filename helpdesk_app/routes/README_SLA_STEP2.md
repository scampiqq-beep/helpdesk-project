SLA v2 — step 2

Что сделано:
- исправлен рендер `/admin/sla-calendar`: `cfg.workdays` снова строка CSV, совместимая с шаблоном;
- `SLAService` стал единой точкой для policy snapshot / context / pause state;
- подготовлен двойной SLA-view: first response + resolve deadline.

Что дальше:
- вывести оба таймера в карточке заявки и списке заявок;
- начать учитывать паузу SLA в UI-состоянии.
