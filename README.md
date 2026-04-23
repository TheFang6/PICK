# 🍱 PICK — Lunch Bot for Office Teams

> ไม่ต้องเสียเวลาถามกันว่า "วันนี้กินอะไรดี?" อีกต่อไป

PICK คือ Telegram Bot ที่ช่วยทีมออฟฟิศตัดสินใจว่าจะไปกินข้าวที่ไหน พร้อมระบบโหวต, Gacha สุ่มร้าน, และ Blacklist ส่วนตัว

---

## ✨ Features

| Feature | คำอธิบาย |
|---------|----------|
| 🎯 แนะนำร้าน | ดึงร้านใกล้ออฟฟิศจาก Google Maps กรองร้านที่เคยไปล่าสุด, ปิดวันนี้, หรือโดน blacklist |
| 🗳️ โหวตในกลุ่ม | เสนอ 3 ร้าน → ทีมกด vote → ประกาศผล |
| 🎲 Gacha | สุ่มใหม่ได้ 5 รอบ ถ้าไม่ชอบตัวเลือก |
| 📍 เช็ค Attendance | `/in` / `/wfh` บอกว่ามาออฟฟิศหรือ WFH |
| 🚫 Blacklist | ไม่ชอบร้านไหน → blacklist ถาวร หรือแค่วันนี้ |
| 🏪 เพิ่มร้านเอง | หาบเร่, โรงอาหาร → `/addrestaurant` เพิ่มได้เลย |
| 📋 ดูประวัติ | Web App ดูประวัติการกินของตัวเองและทีม |

---

## 🏗️ Architecture

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
- **Frontend:** Next.js 16 + TypeScript + shadcn/ui + Tailwind CSS
- **Maps:** Google Maps Places API (Nearby Search)

---

## 🤖 Bot Commands

| Command | Context | Description |
|---------|---------|-------------|
| `/lunch` | Group | สร้าง poll เสนอ 3 ร้าน + ปุ่มโหวต |
| `/lunch` | DM | แสดง 3 ร้าน + ปุ่มยืนยัน |
| `/gacha` | Any | สุ่มร้านเดี่ยว + reroll |
| `/in` | Any | เช็คอิน — มาออฟฟิศวันนี้ |
| `/wfh` | Any | บอกว่า Work from Home |
| `/blacklist add <ชื่อ>` | Any | เพิ่มร้านใน blacklist |
| `/blacklist list` | Any | ดูรายการ blacklist |
| `/blacklist remove <ชื่อ>` | Any | ลบจาก blacklist |
| `/addrestaurant` | Any | เพิ่มร้านด้วยตัวเอง (step-by-step) |
| `/editrestaurant` | Any | แก้ไข/ลบร้านที่เพิ่มเอง |
| `/start` | DM | ลงทะเบียน + รับลิงก์ Web App |
| `/help` | Any | ดูคำสั่งทั้งหมด |

---

## 🔧 Recommendation Pipeline

```
1. Fetch   → Google Maps Nearby Search (up to 20 restaurants)
2. Filter  → ตัดออก: ไปล่าสุด 7 วัน / blacklist / ปิดวันนี้ / นอก radius / rating ต่ำ / รีวิวน้อย
3. Pool    → สุ่ม shuffle → เลือก 10 ร้าน (uniform weight)
4. Sample  → สุ่ม 3 จาก 10 → เสนอทีม
5. Gacha   → roll ใหม่ได้ 5 รอบ จากร้านที่เหลือใน pool
```

**คุณภาพ minimum:**
- Rating ≥ 3.8 (ปรับได้ผ่าน `RATING_THRESHOLD`)
- รีวิว ≥ 20 (ปรับได้ผ่าน `RATINGS_COUNT_THRESHOLD`)

---

## 🚀 Getting Started

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

# Copy และแก้ไข env
cp .env.example .env

# Run migrations
alembic upgrade head

# Start server
uvicorn app.main:app --reload
```

### Frontend Setup

```bash
cd web
npm install

# Copy และแก้ไข env
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
OFFICE_LAT=18.7964464
OFFICE_LNG=99.0164042
OFFICE_RADIUS=5000
WEB_URL=https://your-frontend.up.railway.app
ALLOWED_ORIGINS=https://your-frontend.up.railway.app
RATING_THRESHOLD=3.8
RATINGS_COUNT_THRESHOLD=20
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

## 🗄️ Database Schema

```
users              → ข้อมูลสมาชิกทีม
restaurants        → ร้านอาหาร (Google Maps + manual)
lunch_history      → ประวัติการกิน
user_blacklist     → blacklist ส่วนตัว (permanent / today)
user_attendance    → เช็คอิน IN_OFFICE / WFH / UNKNOWN
poll_sessions      → session การโหวต
poll_votes         → คะแนนโหวตแต่ละคน
pairing_tokens     → เชื่อม Telegram ↔ Web App
web_sessions       → session Web App
```

---

## 🌐 Deploy (Railway)

โปรเจกต์นี้ใช้ Railway all-in-one:

```
Railway Project: pick-food
├── PostgreSQL service
├── Backend service (FastAPI)
└── Frontend service (Next.js)
```

ทั้ง backend และ frontend มี `railway.toml` พร้อมแล้ว push ขึ้น GitHub แล้ว link กับ Railway ได้เลย

---

## 🧪 Tests

```bash
cd backend
pytest tests/unit/ -v
```

มี 19 test files ครอบคลุม: recommendation algorithm, gacha, poll, blacklist, history, attendance, bot handlers, web auth

---

## 📁 Project Structure

```
pick/
├── backend/
│   ├── app/
│   │   ├── api/          # REST endpoints
│   │   ├── bot/          # Telegram bot handlers
│   │   ├── models/       # SQLAlchemy ORM
│   │   ├── schemas/      # Pydantic models
│   │   ├── services/     # Business logic
│   │   └── main.py
│   ├── alembic/          # DB migrations
│   └── tests/
├── web/
│   ├── app/
│   │   ├── blacklist/    # Blacklist management
│   │   ├── history/      # Lunch history calendar
│   │   └── pair/         # Telegram pairing
│   └── components/
├── tasks/                # Task planning files
├── design.md             # Design decisions
└── analyze.md            # Code analysis
```

---

## 🗺️ Roadmap

**POC (ตอนนี้):** Core features ครบ — bot, poll, gacha, blacklist, history, web app

**Next:**
- Deploy backend + frontend บน Railway
- E2E tests (Playwright)

**Future:**
- เก็บเวลาเปิด/ปิดร้านจาก Google Maps (Place Details API)
- Favorites ร้านโปรด
- แจ้งเตือนอัตโนมัติตอนเที่ยง

---

## 👥 Team

Built for a team of 6 people in the same office.
