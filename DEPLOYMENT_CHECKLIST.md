# Deployment Checklist

Use this checklist before treating the live ShelfMate deployment as production-ready.

## 1. Secrets And Access

- [ ] Rotate the Gmail app password if it was ever committed, shared, or pasted anywhere unsafe.
- [ ] Rotate Railway/MySQL credentials if they were exposed outside your private environment.
- [ ] Keep `.env` local only. Do not commit it.
- [ ] Verify Railway web-service variables contain the real production values:
  - `DATABASE_URI`
  - `SECRET_KEY`
  - `SMTP_SERVER`
  - `SMTP_PORT`
  - `SMTP_EMAIL`
  - `SMTP_PASSWORD`
  - `MAIL_USE_TLS`
  - `MAIL_USE_SSL`
  - `MAIL_DEFAULT_SENDER`
  - `ENABLE_MAILER`
  - `SMTP_TIMEOUT`
  - `LOG_LEVEL`

## 2. Database

- [ ] Confirm the live database schema contains:
  - `students.semester`
  - `transactions.due_date`
  - `transactions.return_date`
  - `transactions.admin_note`
  - `transactions.reminder_sent_at`
- [ ] Run the schema sync if needed:

```powershell
.\venv\Scripts\python.exe scripts\sync_transactions_schema.py
```

- [ ] Confirm at least one admin account exists and can log in.
- [ ] Confirm the admin password hash is valid and not truncated.
- [ ] Back up the database before major schema or data changes.

## 3. App Boot

- [ ] Confirm the Railway start command is:

```text
gunicorn wsgi:app --bind 0.0.0.0:$PORT
```

- [ ] Confirm the app boots without `SECRET_KEY`, import, or DB-connection errors.
- [ ] Confirm the public URL loads without `500` on the landing page.

## 4. Core Functional Verification

- [ ] Student registration works.
- [ ] Admin approval works.
- [ ] Student login works after approval.
- [ ] Book add flow works.
- [ ] Student request-book flow works.
- [ ] Admin approve/reject request flow works.
- [ ] Direct issue from student lookup works.
- [ ] Return request and admin confirm-return flow work.
- [ ] Barcode lookup shows transaction details.
- [ ] Overdue rows appear correctly.
- [ ] Reminder email buttons work.
- [ ] Reports page loads.
- [ ] CSV export downloads correctly.

## 5. UX And Device Checks

- [ ] Test the app on desktop width.
- [ ] Test the app on tablet width.
- [ ] Test the app on phone width.
- [ ] Verify table scrolling works on small screens.
- [ ] Verify dark and light theme toggle both remain readable.

## 6. Mail Verification

- [ ] Confirm registration approval email is delivered.
- [ ] Confirm issue approval or direct issue email is delivered.
- [ ] Confirm return confirmation email is delivered.
- [ ] Confirm overdue reminder email is delivered.
- [ ] Check spam/junk if mail seems missing.

## 7. Railway Operational Setup

- [ ] Add a scheduled job for overdue reminders.
- [ ] Record the job command and cadence.
- [ ] Monitor logs after the first scheduled run.
- [ ] Re-run reports export and overdue reminder test after the scheduler is enabled.

## 8. Recommended Final Pass

- [ ] Run a hard refresh in the browser after each deploy.
- [ ] Review Railway logs for unexpected warnings/errors.
- [ ] Commit and push final code changes before production rollout.
