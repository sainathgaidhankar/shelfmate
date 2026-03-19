# TODO Lite

## Phase 1: Production Readiness

- [x] Add production runtime dependencies (`gunicorn`, `PyMySQL`, `Flask-Migrate`)
- [x] Clean config structure for development vs production
- [x] Add startup validation for required settings
- [x] Add application logging
- [x] Add error handlers and production-safe error templates
- [x] Initialize Alembic/Flask-Migrate and create the first tracked migration
- [x] Remove tracked local-only files from Git (`.env`, `__pycache__`, `venv/`)
- [x] Verify app boot + migration commands end to end

## Waiting On User / Background Work

- [ ] Rotate the SMTP/Gmail app password if it has ever been committed, shared, or screenshotted
- [ ] Decide deployment target (`Railway` or `Render`)
- [ ] Create a production MySQL database when deployment prep starts
