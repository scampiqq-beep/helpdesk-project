STEP 14 — knowledge base + admin directories bridge

Что вынесено из legacy_app.py:
- knowledge index / article / favorites / favorite toggle API / templates API
- knowledge manage (categories + articles)
- FAQ add/edit aliases
- admin close reasons CRUD

Что это даёт:
- база знаний и справочники админки больше не живут в монолите;
- знания и причины закрытия теперь идут через service layer;
- сохранена совместимость по старым endpoint-именам и URL.
