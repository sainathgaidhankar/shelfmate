from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import create_app
from app.services.reminder_service import get_overdue_transactions, send_overdue_reminders


def main():
    app = create_app()
    with app.app_context():
        overdue_transactions = get_overdue_transactions()
        sent_count = send_overdue_reminders(overdue_transactions)
        print(f"Sent {sent_count} overdue reminder(s).")


if __name__ == "__main__":
    main()
