# JustBeenPaid-Style 2% × 75-Day Simulation Platform (v2.0.0)

[![Version](https://img.shields.io/badge/version-2.0.0-blue.svg)](https://github.com/mahisalman/MP)
[![Django](https://img.shields.io/badge/Django-5.x%20%2F%204.2-brightgreen.svg)](https://www.djangoproject.com/)
[![Database](https://img.shields.io/badge/Database-MySQL%20%7C%20SQLite%20Fallback-orange.svg)](https://www.mysql.com/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

> [!IMPORTANT]
> **CRITICAL BUSINESS & SAFETY NOTICE — DEMO / SIMULATION SYSTEM ONLY**
>
> This platform is strictly an **educational simulation and test harness**.
> All balances, calculations, and flows use **virtual test credits (DUSD)**.
> - **NO REAL MONEY** is accepted, stored, or processed.
> - **NO CONNECTION** exists to real payment processors, banking networks, or blockchains.
> - **NO FINANCIAL RETURNS** are promised; the 2% daily calculation is purely a mathematical simulation.
> - Global safety kill-switch: `DEMO_MODE = True`. Prominent demo warning banners are rendered across all financial pages.

---

## 🚀 What's New in Version 2.0.0

Version `2.0.0` introduces a complete, production-grade simulation architecture replicating JustBeenPaid-style daily reward and multi-tier referral dynamics with mathematical precision, row locking, and append-only financial accounting:

1. **Deterministic 2% × 75-Day Daily Reward Engine**:
   - Non-compounding linear formula: $\text{daily\_reward} = \text{original\_demo\_amount} \times 0.02$.
   - Position cap at 150% (75 days): 100 DUSD allocated yields exactly 2.00 DUSD/day for 75 days (150 DUSD lifetime cap).
   - Once cap/duration is reached, position automatically marks `COMPLETED`.

2. **Strict Idempotency & Database Locks**:
   - Unique database constraint on `(position, reward_date)` prevents duplicate payments.
   - All balance changes execute within atomic transactions with `select_for_update()` row locking.
   - Unique idempotency keys on every transaction.

3. **Double-Entry Append-Only Demo Ledger**:
   - Every balance movement generates an immutable record with before/after balances.
   - Every description is strictly prefixed with `[DEMO]`.

4. **2-Level Downline Referral Simulation**:
   - **Level 1**: 5% demo bonus credited immediately to direct sponsor upon position allocation.
   - **Level 2**: 2% demo bonus credited to second-tier sponsor.
   - Auto-generated 8-character unique referral codes (`User.referral_code`) with shareable links (`/register/?ref=CODE`).

5. **Simulated Withdrawal Workflow**:
   - User submits request $\rightarrow$ Funds are **locked** in wallet (`locked_balance`).
   - Admin approves $\rightarrow$ moves to `APPROVED`.
   - Admin rejects $\rightarrow$ locked funds immediately **revert** to available balance.
   - Admin completes $\rightarrow$ locked funds permanently deducted with simulated transaction reference.

6. **Interactive Staff Control Panel & CLI Management Suite**:
   - Web UI at `/dashboard/admin-control/` for staff to trigger daily reward batches, approve/reject withdrawals, and view live audit trails.
   - Comprehensive CLI commands:
     - `python manage.py process_daily_rewards [--date YYYY-MM-DD]`
     - `python manage.py seed_demo_data`
     - `python manage.py reconcile_wallets`
     - `python manage.py reconcile_rewards`
     - `python manage.py reset_demo_data --confirm`

---

## 🏗️ Architecture & Modules

```text
django_auth_app/
│
├── accounts/           # User authentication, HMAC 6-digit email verification, profile
├── wallet/             # Demo wallet balances (available/locked), double-entry audit ledger
├── rewards/            # 2% x 75-day simulation engine, positions portfolio, daily distributions
├── referrals/          # Sponsor linking, 2-tier tree (5% L1, 2% L2), bonus distributions
├── withdrawals/        # Simulated fund locking, admin review, rejection refunds, completion
├── dashboard/          # User summary portal, staff simulation control panel
├── audit/              # Immutable audit trail for all security and financial events
│
├── templates/          # Bootstrap 5 responsive templates with demo badges
├── config/             # Django settings, security middleware, database fallback
└── manage.py
```

---

## ⚡ Quick Start Guide

### 1. Prerequisites
- Python 3.10+ (tested on Python 3.13)
- MySQL Server (optional: defaults to SQLite fallback if MySQL is offline)

### 2. Setup Environment
```bash
git clone https://github.com/mahisalman/MP.git
cd MP
pip install -r requirements.txt
```

### 3. Configure Database (`.env`)
```ini
SECRET_KEY=your-secure-secret-key
DEBUG=True
DEMO_MODE=True
USE_SQLITE_FALLBACK=True
```

### 4. Run Migrations & Seed Demo Data
```bash
python manage.py migrate
python manage.py seed_demo_data
```

This automatically configures:
- Default 2% / 75-day simulation plan
- Standard 5% L1 / 2% L2 referral plan
- Demo user accounts (`alice_demo`, `bob_demo`, `charlie_demo` with password `DemoPass123!`)
- 1,000 DUSD simulated credits in each wallet
- A sample 100 DUSD position for Charlie with 5% referral bonus to Bob and 2% to Alice.

### 5. Run the Local Server
```bash
python manage.py runserver 127.0.0.1:8000
```
- **Portal**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Dashboard**: [http://127.0.0.1:8000/dashboard/](http://127.0.0.1:8000/dashboard/)
- **Admin Control Panel**: [http://127.0.0.1:8000/dashboard/admin-control/](http://127.0.0.1:8000/dashboard/admin-control/)
- **Django Admin**: [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/)

---

## 🧪 Automated Testing

To run the automated verification suite covering all mandatory business scenarios:
```bash
python manage.py test rewards
```

Test coverage includes:
- **Scenario 1**: Exact 2% non-compounding calculation over 75 days reaching 150% cap.
- **Scenario 2**: Idempotency and duplicate credit prevention on repeated runs.
- **Scenario 3**: Two-level referral calculations (5% L1, 2% L2).
- **Scenario 4**: Simulated withdrawal fund locking, rejection reversal, and completion.

---

## 🛡️ Versioning & History

- **v1.0.0**: Clean Django authentication portal with custom user model, HMAC-SHA256 6-digit email code verification, password reset, and profile management. (Preserved in branch `release/v1.0.0` and Git tag `v1.0.0`).
- **v2.0.0**: Complete JustBeenPaid-style 2% × 75-day demo simulation platform with 2-level referral network and withdrawal simulator.
