# JobMail Automator 🚀

**JobMail Automator** is a clean, reliable, and lightweight Django web application designed for fresh graduates, software engineers, and job seekers to automate sending personalized cold inquiry emails to companies in controlled daily batches.

---

## 🌟 Core Features

- 📁 **CSV Contact Importer**: Upload contact lists with automatic format validation, column header auto-detection (`company_name`, `email`), and deduplication (in-file and against existing database records).
- ✉️ **Customizable Email Template**: Write a universal job inquiry template with dynamic `{{ company_name }}` variable replacement. Includes live real-time preview.
- ⏱️ **Safe Daily Batch Dispatcher**: Set daily limits (e.g., 50, 75, 100/day) and inter-email delays to respect email service provider sending limits and avoid spam filters.
- 🛡️ **Duplicate & Resend Protection**: Contacts are tracked via database statuses (`Pending`, `Sent`, `Failed`). Contacts already marked as `Sent` are never emailed twice.
- 💻 **CLI Management Command**: Run `python manage.py send_daily_emails` manually or schedule it with **Windows Task Scheduler** or **cron**.
- 📊 **Modern Dashboard**: Visual KPI cards (Total, Pending, Sent, Failed, Daily Limit), delivery progress bars, recent history, and a 1-click batch trigger directly from the web UI.
- 🔍 **Contacts Directory**: Search, status filter, pagination, and a 1-click button to reset failed emails back to `Pending` for retrying.

---

## 🏗️ Project Structure

```
JobMail Automator/
├── manage.py                     # Django CLI entry point
├── requirements.txt              # Project dependencies
├── .env.example                  # Environment variable blueprint
├── .env                          # Local environment variables (SMTP credentials)
├── sample_contacts.csv           # Sample CSV file for quick testing
├── README.md                     # Comprehensive documentation & setup guide
├── config/                       # Core Django project configuration
│   ├── settings.py               # Settings (SMTP, DB, Templates, Apps)
│   ├── urls.py                   # Master URL routing
│   ├── wsgi.py
│   └── asgi.py
└── mailer/                       # Mailer Application
    ├── models.py                 # Contact, EmailTemplate, AppSettings models
    ├── views.py                  # Dashboard, Upload, Template, Contacts views
    ├── forms.py                  # CSV upload and template forms
    ├── services.py               # CSV parsing and batch email dispatch engine
    ├── urls.py                   # Mailer routing
    ├── admin.py                  # Django admin integration
    ├── management/commands/
    │   └── send_daily_emails.py  # CLI daily batch management command
    └── templates/
        ├── base.html             # Base layout (Bootstrap 5 CDN + Icons)
        └── mailer/
            ├── dashboard.html    # Analytics dashboard & batch trigger
            ├── upload_contacts.html # CSV uploader & validation report
            ├── email_template.html  # Template editor & live preview
            └── contacts.html     # Paginated contacts list & filters
```

---

## 🚀 Quick Start & Setup Instructions

### 1. Prerequisites
- **Python 3.10+** installed on your system.

### 2. Create and Activate a Virtual Environment

**On Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```
*(If PowerShell restricts scripts, run `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process` or use Command Prompt: `venv\Scripts\activate.bat`)*

**On macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables (`.env`)
Copy the `.env.example` file to `.env` if not already present:
```bash
cp .env.example .env
```

Open `.env` and fill in your details:
```ini
# Django Settings
SECRET_KEY=your-secure-random-secret-key
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost

# Email Configuration (SMTP)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your_email@gmail.com
EMAIL_HOST_PASSWORD=your_16_character_app_password
DEFAULT_FROM_EMAIL=Dheeraj <your_email@gmail.com>
```

#### 🔑 How to get a Gmail App Password:
1. Go to your [Google Account Settings](https://myaccount.google.com/).
2. Navigate to **Security** & ensure **2-Step Verification** is turned **ON**.
3. In the search bar at the top of your Google Account page, search for **App passwords**.
4. Create a new app password:
   - App name: `JobMail Automator`
5. Copy the generated **16-character code** (e.g. `abcd efgh ijkl mnop`).
6. Paste it into `EMAIL_HOST_PASSWORD` in your `.env` file (without spaces).

---

## 🧪 Testing Before Sending Real Emails

### Option A: Use Console Email Backend (Recommended for 100% Safe Local Testing)
In your `.env` file, set:
```ini
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```
When you trigger sending, emails will be printed cleanly to your terminal instead of being sent over the internet.

### Option B: Dry Run Mode with CLI
Simulate sending without touching the database or sending emails:
```bash
python manage.py send_daily_emails --dry-run
```

### Option C: Test Sending with 1 or 2 Contacts First
1. Upload `sample_contacts.csv` via the web UI.
2. In the Dashboard, click **Trigger Batch Now**, change the batch count to `2`, and submit.
3. Or run via CLI:
```bash
python manage.py send_daily_emails --limit 2
```

---

## 🗄️ Database Migrations

Apply database migrations:
```bash
python manage.py makemigrations
python manage.py migrate
```

*(Optional) Create a superuser to access Django Admin (`/admin/`):*
```bash
python manage.py createsuperuser
```

---

## 🌐 Running the Web Application

Start the development server:
```bash
python manage.py runserver
```

Open your browser and navigate to:
👉 **[http://127.0.0.1:8000/](http://127.0.0.1:8000/)**

---

## 🤖 Automating Daily Batch Sending (Windows Task Scheduler)

To send emails automatically every morning (e.g. 9:00 AM) without manual intervention:

1. Press `Win + R`, type `taskschd.msc`, and press **Enter**.
2. Click **Create Basic Task...** in the right panel.
3. Name it: `JobMail Daily Dispatcher`.
4. Trigger: Choose **Daily** and set your preferred start time (e.g. `09:00:00 AM`).
5. Action: Choose **Start a program**.
6. Settings:
   - **Program/script**: Path to Python inside your virtual environment, e.g.:
     `D:\new Folder of D\Projects\Autonomus mailer\venv\Scripts\python.exe`
   - **Add arguments**: `manage.py send_daily_emails`
   - **Start in**: Path to your project directory:
     `D:\new Folder of D\Projects\Autonomus mailer`
7. Click **Finish**.

---

## 📋 CSV Format Specification

Your CSV file should have a header row with `company_name` and `email`:

```csv
company_name,email
Google,careers@example.com
Microsoft,hr@example.com
ABC Company,hr@abc.com
```

- Duplicate emails are automatically recognized and skipped.
- Malformed email rows are highlighted with clear error messages in the upload report.
