# Django Authentication & Profile Management System with MySQL

A clean, secure, maintainable, and modular **Django 5 web application** with **MySQL** database support, featuring a custom user model, 6-digit email code verification, password reset, education background tracking, and responsive **Bootstrap 5** frontend.

---

## Features Overview

- **Custom User Model**: Inherits from Django's `AbstractUser`, utilizing **Email** as the unique login identifier.
- **Academic & Educational Background**: Tracks highest qualification (`SSC`, `HSC`, `Diploma`, `Bachelor's`, `Master's`, `MPhil`, `PhD`, `Other`), institution, major/subject, and passing year.
- **Bangladesh Mobile Number Validation**: Validates and standardizes BD phone formats (`01712345678`, `+8801712345678`).
- **Cryptographic 6-Digit Email Verification**:
  - Secure random 6-digit generation using Python's `secrets` module.
  - Never stored in plain-text: hashed with HMAC-SHA256 using Django's secret key.
  - Configurable expiration (default 10 minutes).
  - Maximum attempt limiter (default 5 attempts) to prevent brute force.
  - Configurable resend cooldown (default 45 seconds) with interactive JavaScript countdown.
  - Invalidates old codes automatically.
- **Authentication & Security**:
  - Email + Password login.
  - "Remember Me" session persistence (2 weeks vs browser close).
  - Generic error messages to prevent email/account enumeration.
  - Blocks unverified users and routes them to verification.
  - Session protection, CSRF protection, and production security headers.
- **User Dashboard & Profile**:
  - Overview dashboard.
  - Full personal and academic profile view.
  - Profile edit form (strictly protects email and administrative flags).
  - In-app password change with session preservation.
- **Password Reset**:
  - Full single-use token password reset flow via email.
  - Generic confirmation prevents user enumeration.
- **Django Admin**:
  - Custom user admin with filters, search, and fieldsets.
  - Read-only audit log for verification code requests.

---

## Project Structure

```text
django_auth_app/
│
├── manage.py
├── requirements.txt
├── .env
├── .env.example
├── .gitignore
├── README.md
│
├── config/
│   ├── __init__.py           # Registers PyMySQL as MySQLdb driver
│   ├── settings.py           # Core settings, MySQL config, security policies
│   ├── urls.py               # Main URL router
│   ├── wsgi.py
│   └── asgi.py
│
├── accounts/
│   ├── migrations/
│   │   └── 0001_initial.py
│   ├── templates/
│   │   └── accounts/
│   │       ├── emails/
│   │       │   ├── verification_email.html
│   │       │   ├── verification_email.txt
│   │       │   ├── password_reset_email.html
│   │       │   ├── password_reset_email.txt
│   │       │   └── password_reset_subject.txt
│   │       ├── register.html
│   │       ├── verify_email.html
│   │       ├── login.html
│   │       ├── dashboard.html
│   │       ├── profile.html
│   │       ├── edit_profile.html
│   │       ├── change_password.html
│   │       ├── forgot_password.html
│   │       ├── forgot_password_done.html
│   │       ├── reset_password.html
│   │       └── reset_password_complete.html
│   │
│   ├── admin.py              # Custom UserAdmin and EmailVerificationCodeAdmin
│   ├── apps.py
│   ├── forms.py              # Registration, Login, Verification & Profile forms
│   ├── models.py             # User & EmailVerificationCode models
│   ├── services.py           # Business logic, email dispatch & code validation
│   ├── tests.py              # 22 comprehensive automated tests
│   ├── urls.py               # Clean URLs for accounts app
│   └── views.py              # Thin view handlers
│
├── templates/
│   ├── base.html             # Responsive Bootstrap 5 layout & navbar
│   ├── home.html             # Landing page
│   └── includes/
│       └── messages.html     # Dismissible Bootstrap alert banners
│
└── static/
    ├── css/
    │   └── style.css         # Modern styling & code input formatting
    └── js/
        └── main.js           # Resend countdown timer & digit auto-formatting
```

---

## Installation & Setup

### 1. Prerequisites
- **Python 3.10+** (Tested on Python 3.13)
- **MySQL 8.x** or **MariaDB**
- `pip` package manager

### 2. Clone or Navigate to Project
```powershell
cd C:\Users\MAHI-IT\.gemini\antigravity\scratch\django_auth_app
```

### 3. Create & Activate Virtual Environment
On Windows:
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```
On Linux/macOS:
```bash
python3 -m venv venv
source venv/bin/activate
```

### 4. Install Dependencies
```powershell
pip install -r requirements.txt
```
*(Note: `PyMySQL` is installed to ensure cross-platform MySQL connectivity without requiring separate C-compilers).*

---

## Database Configuration

### 1. Create the MySQL Database
Log into MySQL CLI or MySQL Workbench:
```sql
CREATE DATABASE django_auth_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 2. Configure `.env`
Copy `.env.example` to `.env` (if not already done) and adjust your credentials:
```ini
SECRET_KEY=your-secure-secret-key-for-django
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# MySQL Configuration
DB_ENGINE=django.db.backends.mysql
DB_NAME=django_auth_db
DB_USER=root
DB_PASSWORD=your_actual_mysql_password
DB_HOST=127.0.0.1
DB_PORT=3306

# Set to False once your MySQL service is running
USE_SQLITE_FALLBACK=False

# Email Configuration
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
DEFAULT_FROM_EMAIL="Django Auth Portal <no-reply@example.com>"

# Security & Verification Code Limits
VERIFICATION_CODE_EXPIRY_MINUTES=10
VERIFICATION_CODE_RESEND_COOLDOWN_SECONDS=45
VERIFICATION_CODE_MAX_ATTEMPTS=5
```

---

## Database Migrations & Initial Setup

### 1. Run Migrations
```powershell
python manage.py makemigrations
python manage.py migrate
```

### 2. Create Superuser (Admin)
```powershell
python manage.py createsuperuser
```
Follow the interactive prompt (enter email, full name, mobile number, and admin password).

### 3. Run Development Server
```powershell
python manage.py runserver
```

Open your browser and navigate to:
- **Application**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Admin Panel**: [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/)

---

## How Email Verification Works in Development

During local development, `EMAIL_BACKEND` is set to `django.core.mail.backends.console.EmailBackend`.

1. When you register a new account or request a password reset, **the email is printed directly to your console/terminal** where `runserver` is running.
2. Locate the 6-digit verification code in the terminal output:
   ```text
   Your 6-digit email verification code is:
   583214
   ```
3. Type `583214` into the verification screen in your browser and click **Verify Email**.

---

## Configuring Real Email Delivery (SMTP)

To send real emails (e.g. using Gmail SMTP or Amazon SES):

1. In `.env`, change:
   ```ini
   EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
   EMAIL_HOST=smtp.gmail.com
   EMAIL_PORT=587
   EMAIL_USE_TLS=True
   EMAIL_HOST_USER=your_email@gmail.com
   EMAIL_HOST_PASSWORD=your_16_character_app_password
   DEFAULT_FROM_EMAIL="Your App Name <your_email@gmail.com>"
   ```
2. For Gmail, enable 2-Factor Authentication on your Google account and generate an **App Password** from Google Account Security.

---

## Running Automated Tests

Run the complete test suite:
```powershell
python manage.py test accounts
```
Expected output:
```text
Ran 22 tests in 16.004s

OK
```

The test suite covers:
- User registration (valid data, duplicate email/phone, invalid phone, DOB limits, password mismatch).
- 6-digit verification (valid code, wrong code, expired code, max attempts lockout, resend cooldown).
- Authentication (login with email, wrong password, unverified user blocked, remember me session, logout).
- Profile (view profile, update fields, security protections for immutable fields).
- Password reset (email link generation, enumeration prevention, valid password change).

---

## Production Readiness Checklist

When deploying to a production environment (Linux VPS, Nginx, Gunicorn, MySQL):

1. **Environment Variables**:
   - Set `DEBUG=False`.
   - Provide a long, cryptographically random `SECRET_KEY`.
   - Update `ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com`.
2. **Database**:
   - Ensure MySQL database uses `utf8mb4`.
   - Set `USE_SQLITE_FALLBACK=False`.
3. **Security Headers**:
   - When `DEBUG=False`, Django automatically activates secure session cookies, secure CSRF cookies, XSS filtering, and strict X-Frame-Options.
   - Configure HTTPS with Let's Encrypt (Certbot) on Nginx.
4. **Static Files**:
   ```bash
   python manage.py collectstatic --noinput
   ```
5. **WSGI Server**:
   ```bash
   gunicorn --workers 3 --bind 127.0.0.1:8000 config.wsgi:application
   ```
