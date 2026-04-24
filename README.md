# PICK — Lunch Bot for Office Teams

> ไม่ต้องเสียเวลาถามกันว่า "วันนี้กินอะไรดี?" อีกต่อไป

PICK คือ Telegram Bot ที่ช่วยทีมออฟฟิศตัดสินใจว่าจะไปกินข้าวที่ไหน พร้อมระบบโหวต, Gacha สุ่มร้าน, และ Blacklist ส่วนตัว

---

## Features

| Feature | คำอธิบาย |
|---------|----------|
| แนะนำร้าน | ดึงร้านใกล้ออฟฟิศจาก Google Maps กรองร้านที่เคยไปล่าสุด, ปิดวันนี้, หรือโดน blacklist |
| โหวตในกลุ่ม | เสนอ 3 ร้าน → ทีมกด vote → ประกาศผล |
| Gacha | สุ่มใหม่ได้ 5 รอบต่อ session ถ้าไม่ชอบตัวเลือก |
| เช็ค Attendance | `/in` / `/wfh` บอกว่ามาออฟฟิศหรือ WFH |
| Blacklist | ไม่ชอบร้านไหน → blacklist ถาวร หรือแค่วันนี้ |
| เพิ่มร้านเอง | หาบเร่, โรงอาหาร → `/addrestaurant` เพิ่มได้เลย |
| ดูประวัติ | Web App ดูประวัติการกินของตัวเองและทีม |

---

## Architecture

```
Telegram Group Chat
       │
       ▼
 Telegram Bot (python-telegram-bot)
       │
       ▼
 FastAPI Backend ──── PostgreSQL (Railway)
       │
       ├── Google Maps Places API
       └── Next.js Web App (blacklist, history)
```

**Tech Stack:**
- **Backend:** Python 3.12 + FastAPI + SQLAlchemy + Alembic
- **Bot:** python-telegram-bot v20+
- **Database:** PostgreSQL (via Railway)
- **Frontend:** Next.js + TypeScript + shadcn/ui + Tailwind CSS
- **Maps:** Google Maps Places API (Nearby Search)

---

## Bot Commands

| Command | Description |
|---------|-------------|
| `/lunch` | สร้าง poll เสนอ 3 ร้าน + ปุ่มโหวต (group) / แสดงตัวเลือก (DM) |
| `/gacha` | สุ่มร้านเดี่ยว + reroll ได้ 5 รอบ |
| `/in` | เช็คอิน — มาออฟฟิศวันนี้ |
| `/wfh` | บอกว่า Work from Home |
| `/blacklist add <ชื่อ>` | เพิ่มร้านใน blacklist |
| `/blacklist list` | ดูรายการ blacklist |
| `/blacklist remove <ชื่อ>` | ลบจาก blacklist |
| `/addrestaurant` | เพิ่มร้านด้วยตัวเอง (step-by-step) |
| `/editrestaurant` | แก้ไข/ลบร้านที่เพิ่มเอง |
| `/start` | ลงทะเบียน + รับลิงก์ Web App |
| `/help` | ดูคำสั่งทั้งหมด |

---

## Recommendation Pipeline

```
1. Fetch   → Google Maps Nearby Search (สูงสุด 20 ร้านต่อ request)
2. Filter  → ตัดออก: ไปล่าสุด 7 วัน / blacklist / ปิดวันนี้ / 
             ปิดตามวัน (closed_weekdays) / ปิดตามช่วงวันที่ (closed_monthly_ranges) /
             นอก radius / rating ต่ำ / รีวิวน้อย
3. Pool    → Random shuffle → เลือก 10 ร้าน
4. Sample  → สุ่ม 3 จาก 10 → เสนอทีม
5. Gacha   → roll ใหม่ได้สูงสุด 5 รอบ (MAX_GACHA_ROLLS) จากร้านที่เหลือใน pool
```

**คุณภาพ minimum (ปรับได้ผ่าน env vars):**
- Rating ≥ 3.8 (`RATING_THRESHOLD`)
- รีวิว ≥ 20 (`RATINGS_COUNT_THRESHOLD`)

**Session pool:** เก็บใน memory, TTL 2 ชั่วโมง

---

## Getting Started

### Prerequisites
- Python 3.12+
- Node.js 20+
- PostgreSQL (หรือ Railway)
- Google Maps API Key
- Telegram Bot Token (จาก @BotFather)

### Backend Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env

alembic upgrade head

uvicorn app.main:app --reload
```

### Frontend Setup

```bash
cd web
npm install
cp .env.example .env.local
npm run dev
```

### Environment Variables

**Backend (`.env`):**

```env
DATABASE_URL=postgresql://user:pass@host:5432/pick
GOOGLE_MAPS_API_KEY=your_key_here
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_WEBHOOK_SECRET=optional_secret
BASE_URL=https://your-backend.up.railway.app
ALLOWED_ORIGINS=https://your-frontend.up.railway.app
WEB_URL=https://your-frontend.up.railway.app
OFFICE_LAT=18.7964464
OFFICE_LNG=99.0164042
OFFICE_RADIUS=1000
RATING_THRESHOLD=3.8
RATINGS_COUNT_THRESHOLD=20
DEBUG=false
```

**Frontend (`.env.local`):**

```env
NEXT_PUBLIC_API_URL=https://your-backend.up.railway.app
```

### Set Telegram Webhook

```bash
curl -X POST https://your-backend.up.railway.app/webhook/set
```

---

## Database Schema

```
users                → ข้อมูลสมาชิกทีม (telegram_id, name)
restaurants          → ร้านอาหาร (Google Maps + manual)
                       - closed_weekdays: วันปิดประจำสัปดาห์ (0=จันทร์, 6=อาทิตย์)
                       - closed_monthly_ranges: ช่วงวันที่ปิดในแต่ละเดือน
lunch_history        → ประวัติการกิน (restaurant_id, date, attendees)
user_blacklist       → blacklist ส่วนตัว (permanent / today)
user_attendance      → เช็คอิน IN_OFFICE / WFH / UNKNOWN
poll_sessions        → session การโหวต (candidates, status, winner)
poll_votes           → คะแนนโหวตแต่ละคน
pairing_tokens       → เชื่อม Telegram ↔ Web App
web_sessions         → session Web App
```

---

## API Routes

| Prefix | Description |
|--------|-------------|
| `/recommend` | สร้าง recommendation pool |
| `/gacha/{session_id}` | reroll จาก session pool |
| `/blacklist` | CRUD blacklist |
| `/history` | ดูประวัติการกิน |
| `/restaurants` | CRUD ร้านอาหาร |
| `/attendance` | เช็คอิน/WFH |
| `/pair` | Telegram ↔ Web App pairing |
| `/telegram` | Telegram webhook |
| `/health` | Health check |

---

## Deploy (Railway)

โปรเจกต์นี้ใช้ Railway all-in-one:

```
Railway Project: pick-food
├── PostgreSQL service
├── Backend service (FastAPI)
└── Frontend service (Next.js)
```

ทั้ง backend และ frontend มี `railway.toml` พร้อมแล้ว — push ขึ้น GitHub แล้ว link กับ Railway ได้เลย

---

## Tests

```bash
cd backend
pytest tests/unit/ -v
```

มี 17 test files ครอบคลุม: recommendation algorithm, gacha, poll, blacklist, history, attendance, bot handlers, web auth, Google Maps integration

---

## Project Structure

```
pick/
├── backend/
│   ├── app/
│   │   ├── api/          # REST endpoints
│   │   ├── bot/
│   │   │   └── handlers/ # Telegram bot command handlers
│   │   ├── models/       # SQLAlchemy ORM models
│   │   ├── schemas/      # Pydantic models
│   │   ├── services/     # Business logic (recommendation, gacha, session pool)
│   │   ├── config.py     # App configuration (env vars)
│   │   └── main.py
│   ├── alembic/          # DB migrations (8 versions)
│   └── tests/unit/       # Unit tests (17 files)
├── web/
│   ├── app/
│   │   ├── blacklist/    # Blacklist management
│   │   ├── history/      # Lunch history
│   │   └── pair/         # Telegram pairing
│   └── components/
├── tasks/                # Task planning files
├── design.md             # Design decisions
└── analyze.md            # Code analysis
```

---

## Roadmap

**POC (ตอนนี้):** Core features ครบ — bot, poll, gacha, blacklist, history, web app

**Next:**
- Deploy backend + frontend บน Railway
- E2E tests (Playwright)

**Future:**
- เก็บเวลาเปิด/ปิดร้านจาก Google Maps (Place Details API)
- Favorites ร้านโปรด
- แจ้งเตือนอัตโนมัติตอนเที่ยง
- Price level filtering

---

Built for a team of 6 people in the same office.
