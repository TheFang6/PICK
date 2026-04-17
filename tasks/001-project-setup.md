# 001 — Project Setup

**Phase:** 1 (Foundation)
**Estimated Time:** 4-6 ชม.
**Dependencies:** None

---

## 🎯 Goal

Setup FastAPI project structure + Railway PostgreSQL + local dev environment ให้พร้อมเขียนโค้ด

---

## ✅ Subtasks

### Backend Project Structure

- [ ] สร้าง Git repo (monorepo: `backend/`, `web/`)
- [ ] สร้าง Python virtual environment (Python 3.11+)
- [ ] Install dependencies:
  - [ ] `fastapi`
  - [ ] `uvicorn[standard]`
  - [ ] `sqlalchemy`
  - [ ] `alembic`
  - [ ] `psycopg2-binary`
  - [ ] `python-telegram-bot` v20+
  - [ ] `httpx` (for Google Maps API calls)
  - [ ] `pydantic-settings`
  - [ ] `python-dotenv`
- [ ] สร้างโครงสร้างไฟล์:
  ```
  backend/
  ├── app/
  │   ├── __init__.py
  │   ├── main.py
  │   ├── config.py
  │   ├── database.py
  │   ├── models/
  │   ├── schemas/
  │   ├── api/
  │   ├── services/
  │   └── utils/
  ├── alembic/
  ├── tests/
  ├── .env.example
  ├── requirements.txt
  └── README.md
  ```

### Database Setup

- [ ] Railway: สร้าง project + เพิ่ม PostgreSQL plugin
- [ ] Copy `DATABASE_URL` จาก Railway → local `.env`
- [ ] Test connection จาก local ไป Railway PostgreSQL
- [ ] Setup Alembic:
  - [ ] `alembic init alembic`
  - [ ] Config `alembic.ini` → อ่าน `DATABASE_URL` จาก env
  - [ ] Config `env.py` ให้ใช้ SQLAlchemy metadata

### Basic FastAPI App

- [ ] `main.py` — สร้าง FastAPI instance + CORS middleware
- [ ] Health check endpoint: `GET /health` → `{"status": "ok"}`
- [ ] `config.py` — Pydantic Settings อ่าน env vars
- [ ] Run locally: `uvicorn app.main:app --reload`
- [ ] Test `http://localhost:8000/health` ✅

### Development Tools

- [ ] `.gitignore` — ไม่ commit `.env`, `__pycache__/`, `.venv/`
- [ ] Pre-commit hook (optional): black, ruff
- [ ] `.env.example` พร้อม placeholders

---

## 📋 Acceptance Criteria

✅ `/health` endpoint ตอบ 200 OK
✅ เชื่อมต่อ Railway PostgreSQL ได้จาก local
✅ `alembic current` ไม่ error
✅ `.env` ไม่อยู่ใน git
✅ README มีขั้นตอน setup ครบ

---

## 📝 Technical Notes

- Python 3.11+ เพราะ `python-telegram-bot` v20 ต้องการ async syntax ใหม่
- ใช้ SQLAlchemy 2.0 style (ไม่ใช่ legacy)
- Alembic ตั้งให้ auto-generate จาก models
- Railway PostgreSQL internal URL ใช้ SSL required → ใส่ `?sslmode=require` ถ้า error

## 🔗 Reference

- `design.md` → Tech Stack section
- `integrate-railway.md` → Railway setup details
