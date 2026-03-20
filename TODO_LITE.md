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

## Phase 2: Core Product Improvements

- [x] Add book search, filter, sort, and pagination
- [x] Add overdue tracking and overdue visibility
- [x] Add admin rejection actions with reasons
- [x] Sync the database schema for new Phase 2 fields (`transactions.admin_note`)
- [x] Verify updated student/admin workflows locally and on Railway

## Phase 3: Admin Operations Dashboard

- [x] Build a dedicated admin student lookup screen
- [x] Add filters for department and semester/year (`1st` to `8th`) on the lookup screen
- [x] Add student lookup by USN with a filtered-list workflow
- [x] Show student summary after lookup: profile, contact, total books, issued books, pending returns, returned books
- [x] Show per-student transaction list with clear statuses and due dates
- [x] Add manual issue flow from the student lookup screen for walk-in library requests
- [x] Add manual return / mark-return shortcut from the admin student screen and barcode detail flow
- [x] Add an overdue students dashboard card/table with name, USN, contact, and pending books
- [x] Add overdue email reminder sending for students whose due date has passed
- [x] Decide reminder trigger strategy: automatic scheduled job plus manual "send reminders now" action
- [x] Improve admin dashboard UI into a cleaner operations layout with dedicated sections for lookup, approvals, requests, and overdue follow-up

## Recommended Build Order

- [x] Step 1: Student lookup page with department/semester filters and USN search
- [x] Step 2: Student detail panel with current books, pending returns, and history
- [x] Step 3: Manual issue-book action from the student detail page
- [x] Step 4: Overdue students table on admin dashboard
- [x] Step 5: Email reminder sending for overdue students

## Phase 4: Reporting And Hardening

- [x] Add an admin reports screen with filters for status, department, USN, and date range
- [x] Add CSV export for filtered circulation reports
- [x] Add an academic-cycle admin workflow for bulk semester updates by department/section/current semester
- [ ] Configure Railway scheduled job for automatic overdue reminders
- [x] Add a final deployment hardening / post-deploy checklist
