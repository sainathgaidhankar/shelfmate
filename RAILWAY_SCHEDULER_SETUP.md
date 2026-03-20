# Railway Scheduler Setup

This project already contains the reminder runner:

```text
scripts/send_overdue_reminders.py
```

The remaining step is to create a scheduled Railway job that runs it automatically.

## Command To Run

Use this command for the scheduled job:

```text
python scripts/send_overdue_reminders.py
```

If Railway requires the project venv-aware command internally, use the normal Python command that Railway exposes in the deployed container. For standard Railway Python services, `python ...` is correct.

## Recommended Schedule

For a library workflow, a daily schedule is enough.

Recommended:

```text
Once every day at 09:00 AM
```

If Railway asks for a cron expression, use:

```text
0 9 * * *
```

Adjust the schedule if you want the reminder to run at a different hour.

## Railway Steps

1. Open your Railway project.
2. Open the service that contains the ShelfMate app.
3. Create a new scheduled job / cron job.
4. Use this command:

```text
python scripts/send_overdue_reminders.py
```

5. Set the schedule to daily.
6. Save the job.
7. Trigger one manual run first to verify it works.

## What To Verify After Setup

After the first run:

- Check Railway logs for the output:

```text
Sent X overdue reminder(s).
```

- Confirm overdue students received the email.
- Confirm `transactions.reminder_sent_at` was updated for those rows.
- Confirm the admin dashboard shows `Sent Today` for reminders already sent that day.

## If The Job Fails

Check these first:

- `DATABASE_URI` exists in the Railway environment.
- SMTP variables are correct.
- `ENABLE_MAILER=True`
- The DB schema includes `transactions.reminder_sent_at`

If schema sync is still needed, run:

```powershell
.\venv\Scripts\python.exe scripts\sync_transactions_schema.py
```

## Manual Fallback

Even without the scheduler, reminders can still be sent from the admin dashboard:

- `Send Reminder`
- `Send All Reminders`
