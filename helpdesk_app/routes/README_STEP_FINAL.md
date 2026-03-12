Final architecture closeout:

- removed obsolete compatibility shims: `legacy_app.py`, `models.py`, `helpdesk_app/models/core.py`;
- `legacy_monolith.py` now imports models from `helpdesk_app.models`;
- route/service/domain/models structure remains the primary project architecture;

Important: one legacy runtime file still remains: `legacy_monolith.py`.
This archive closes the architecture migration enough to stop further shim work and move to product features.
