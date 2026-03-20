# ShelfMate

ShelfMate is a Flask-based library management web application for colleges and departments. It supports student registration and approval, book issue and return workflows, barcode lookup, overdue reminders, reports, academic batch updates, approval-based student profile changes, and a responsive admin/student interface.

## Features

- Student registration with approval flow
- Admin dashboard for issue, return, approvals, and overdue tracking
- Book catalog with search, filters, direct issue, and admin edit controls
- Barcode-based transaction lookup
- Reminder emails for overdue books
- Reports with CSV export
- Bulk academic updates for semester promotion and completion
- Optional student profile images and book cover images
- Student profile update requests for contact, section, and profile image with admin approval
- Unavailable book cards with separate visual state when copies reach zero
- Railway-ready production setup

## Tech Stack

- Python 3.12+
- Flask
- Flask-SQLAlchemy
- Flask-Migrate
- Flask-Login
- Flask-WTF
- MySQL
- PyMySQL
- Tailwind via CDN

## Project Structure

```text
shelfmate/
|-- app/
|   |-- models/
|   |-- routes/
|   |-- services/
|   |-- static/
|   |   |-- images/
|   |   `-- uploads/
|   `-- templates/
|-- migrations/
|-- scripts/
|-- app.py
|-- config.py
|-- models.py
|-- requirements.txt
`-- wsgi.py
```

## Local Installation

### 1. Clone the project

```bash
git clone <your-repository-url>
cd shelfmate
```

### 2. Create and activate a virtual environment

Windows PowerShell:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

macOS / Linux:

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Copy `.env.example` to `.env` and update the values.

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Required values:

```env
DATABASE_URI=mysql+pymysql://root:password@localhost/shelfmate_db
SECRET_KEY=replace_with_a_secure_secret
FLASK_ENV=development
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_EMAIL=your_email@gmail.com
SMTP_PASSWORD=your_app_password
MAIL_USE_TLS=True
MAIL_USE_SSL=False
MAIL_DEBUG=0
MAIL_DEFAULT_SENDER=your_email@gmail.com
ENABLE_MAILER=True
SMTP_TIMEOUT=10
LOG_LEVEL=INFO
```

## Database Setup

### 1. Create the MySQL database

```sql
CREATE DATABASE shelfmate_db;
```

### 2. Run migrations / schema sync

If you are using the current project schema, run:

```powershell
.\venv\Scripts\python.exe scripts\sync_transactions_schema.py
```

If you are working with Flask-Migrate on a fresh database:

```powershell
.\venv\Scripts\flask.exe db upgrade
```

## Running the Application

### Development

```powershell
.\venv\Scripts\python.exe app.py
```

Then open:

```text
http://127.0.0.1:5000
```

### Production-style local run

```powershell
.\venv\Scripts\gunicorn.exe wsgi:app --bind 0.0.0.0:5000
```

## Default Admin Setup

Create an admin user directly in the database or through your existing admin seed flow. The app expects admin accounts to be stored in the `students` table with:

- `approved = 1`
- `is_admin = 1`

## Image Uploads

- Student profile image upload is optional during registration
- Book cover upload is optional while adding books
- Students can later request profile image, contact, and section changes for admin approval
- Admins can update book details and replace book cover images from the catalog
- If no image is uploaded, ShelfMate uses default placeholder images
- Uploaded files are stored inside:
  - `app/static/uploads/students/`
  - `app/static/uploads/books/`

## Useful Scripts

- Sync schema:
  ```powershell
  .\venv\Scripts\python.exe scripts\sync_transactions_schema.py
  ```
- Send overdue reminders manually:
  ```powershell
  .\venv\Scripts\python.exe scripts\send_overdue_reminders.py
  ```

## Deployment Notes

- Use `wsgi.py` as the production entrypoint
- Set environment variables in your hosting platform
- For production deployment, use a managed MySQL database and a proper WSGI server such as Gunicorn

## Final QA Checklist

- Register a student with and without image
- Add a book with and without cover
- Approve and reject student registrations
- Submit and approve or reject a student profile update request
- Edit a book and verify updated stock/image values
- Set a book to zero available copies and verify the student card shows unavailable
- Request, issue, and return a book
- Test barcode lookup
- Test overdue reminder emails
- Test academic bulk updates
- Test report export
- Verify mobile and desktop layouts

## License

Add your preferred license before sharing with clients or publishing publicly.
