# Private School Telegram Bot + Hikvision FaceID Attendance (Production-Ready Skeleton)

This repository contains a modular Telegram bot (aiogram v3) + FastAPI server for Hikvision FaceID attendance events, using:

- Python 3.11+
- PostgreSQL (SQLAlchemy 2.0 async + Alembic migrations)
- Redis (aiogram FSM storage potential + throttling + brute-force + attendance dedupe)
- Google Sheets sync (hourly with APScheduler)
- Google Sheets attendance logging per-branch (daily tab DD.MM.YYYY)
- Clean-ish architecture separation: core / models / repositories / services / bot routers

Timezone: **Asia/Tashkent**.

---

## What is implemented (MVP but runnable)

### Auth / RBAC
- `/start` shows exact required buttons for guests.
- Parent login & bind student:
  - Parent uses **FM12345 + password** (password hash verified)
  - A Telegram user can bind multiple students
- Employee login:
  - Employee uses **FX12345 + password**
  - Telegram user is bound to one employee profile

### Brute force protection
- 5 failures -> blocked for 10 minutes (Redis)

### Teacher module (MVP)
- Enter grade (class name -> student FM -> score -> optional comment/date)
- Add homework (class name -> text -> optional deadline)
- Complaint (target PARENT/MANAGEMENT)

### Parent module (MVP)
- Bind multiple students
- View: My children, latest grades/homeworks/payments
- Feedback (SUGGESTION/COMPLAINT) -> admins inbox list

### Cashier module (MVP)
- Create payment -> DB + attempt write to Sheets tab `payments`
- If sheets write fails -> marked FAILED and retried by scheduler
- Notifies parents with exact receipt template

### HR module (MVP)
- List employees, set active/inactive
- Reset employee password

### Admin module (MVP)
- Manual sync from Sheets
- Credential reset FM/FX
- Feedback inbox
- Audit log
- FaceID admin: add branch, add device, bind attendance notification chat_id

### Face enrollment (selfie)
- Employee sends selfie photo
- Bot uploads to all devices in employee’s branch via Digest auth client (scaffold; endpoints may vary by firmware)
- Returns per-device report

### Hikvision attendance server (FastAPI)
- POST `/api/hikvision/event`
- Extracts device IP and employee UID (FXxxxxx) from payload
- Dedupe (Redis TTL)
- Writes attendance to branch’s `attendance_sheet_id` creating daily tab **DD.MM.YYYY**
- Sends Telegram notification (via Bot API HTTP) to employee.notification_chat_id if set

---

## Repository layout

- `app/bot/` aiogram routers + middlewares + FSM states
- `app/core/` config, db, redis, sheets, hikvision server/client
- `app/models/` SQLAlchemy models
- `app/repositories/` DB access layer
- `app/services/` sync