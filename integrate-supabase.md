# Supabase Integration Guide — PICK (Food)

> Setup Supabase เป็น PostgreSQL backend สำหรับ project นี้

---

## 1. สร้าง Supabase Project

1. ไปที่ [supabase.com](https://supabase.com) → Sign in / Sign up
2. คลิก **New Project**
3. กรอกข้อมูล:
   - **Name:** `pick-food`
   - **Database Password:** ตั้งรหัสผ่านแข็งแรง (เก็บไว้ใช้ทีหลัง)
   - **Region:** `Southeast Asia (Singapore)` — ใกล้ไทยสุด
4. รอ ~2 นาที ระบบ provision เสร็จ

---

## 2. รัน Database Schema

ไปที่ **SQL Editor** (เมนูซ้าย) → คลิก **New Query** → วาง SQL ด้านล่างแล้วกด **Run**

```sql
-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Users
CREATE TABLE users (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    telegram_id   TEXT UNIQUE NOT NULL,
    name          TEXT,
    location_lat  FLOAT,
    location_lng  FLOAT,
    created_at    TIMESTAMP DEFAULT NOW()
);

-- Restaurants (Hybrid: Google Maps + Manual)
CREATE TABLE restaurants (
    id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source                 TEXT NOT NULL CHECK (source IN ('google_maps', 'manual')),
    google_place_id        TEXT,
    name                   TEXT NOT NULL,
    lat                    FLOAT,
    lng                    FLOAT,
    avg_price              INT,
    price_level            INT CHECK (price_level BETWEEN 1 AND 4),
    category               TEXT,
    closed_weekdays        INT[],   -- [0=Mon, 1=Tue, ..., 6=Sun]
    closed_monthly_ranges  JSONB,   -- [{"start":1,"end":3},{"start":15,"end":17}]
    closing_note           TEXT,
    added_by               TEXT,    -- telegram_id
    group_id               TEXT,    -- Telegram chat_id
    created_at             TIMESTAMP DEFAULT NOW()
);

-- Personal Blacklist
CREATE TABLE user_blacklist (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    restaurant_id   UUID REFERENCES restaurants(id) ON DELETE CASCADE,
    note            TEXT,
    created_at      TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, restaurant_id)
);

-- Lunch History
CREATE TABLE lunch_history (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    restaurant_id   UUID REFERENCES restaurants(id) ON DELETE SET NULL,
    restaurant_name TEXT NOT NULL,  -- snapshot ชื่อ ณ เวลานั้น
    eaten_at        DATE NOT NULL DEFAULT CURRENT_DATE,
    created_at      TIMESTAMP DEFAULT NOW()
);

-- Attendance Tracking
CREATE TABLE user_attendance (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID REFERENCES users(id) ON DELETE CASCADE,
    group_id    TEXT NOT NULL,
    date        DATE NOT NULL DEFAULT CURRENT_DATE,
    status      TEXT NOT NULL CHECK (status IN ('in_office', 'wfh', 'unknown')) DEFAULT 'unknown',
    updated_at  TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, group_id, date)
);

-- Poll Session
CREATE TABLE poll_session (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    group_id    TEXT NOT NULL,
    options     JSONB NOT NULL,  -- [{restaurant_id, name, distance_km, avg_price, source}]
    expires_at  TIMESTAMP NOT NULL,
    status      TEXT NOT NULL CHECK (status IN ('active', 'completed', 'timeout')) DEFAULT 'active',
    winner_id   UUID REFERENCES restaurants(id) ON DELETE SET NULL,
    created_at  TIMESTAMP DEFAULT NOW()
);

-- Poll Votes
CREATE TABLE poll_votes (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id      UUID REFERENCES poll_session(id) ON DELETE CASCADE,
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    restaurant_id   UUID REFERENCES restaurants(id) ON DELETE CASCADE,
    created_at      TIMESTAMP DEFAULT NOW(),
    UNIQUE(session_id, user_id)  -- 1 คน 1 โหวตต่อ session
);

-- Indexes
CREATE INDEX idx_restaurants_group ON restaurants(group_id);
CREATE INDEX idx_history_user_date ON lunch_history(user_id, eaten_at DESC);
CREATE INDEX idx_attendance_group_date ON user_attendance(group_id, date);
CREATE INDEX idx_poll_group_status ON poll_session(group_id, status);
```

---

## 3. เก็บ Credentials

ไปที่ **Settings → Database** → copy connection string

```
Settings → Database → Connection string → URI
```

หน้าตาแบบนี้:
```
postgresql://postgres:[YOUR-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres
```

สร้างไฟล์ `.env` ใน root ของ FastAPI project:
```env
DATABASE_URL=postgresql+asyncpg://postgres:[YOUR-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres
SUPABASE_URL=https://[PROJECT-REF].supabase.co
SUPABASE_ANON_KEY=[YOUR-ANON-KEY]
```

> ⚠️ อย่า commit `.env` ขึ้น git เด็ดขาด — เพิ่ม `.env` ใน `.gitignore`

---

## 4. FastAPI — Database Connection

```bash
pip install sqlalchemy[asyncio] asyncpg python-dotenv
```

สร้างไฟล์ `app/database.py`:
```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os

load_dotenv()

engine = create_async_engine(os.getenv("DATABASE_URL"), echo=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
```

ทดสอบ connection:
```python
# test_db.py
import asyncio
from app.database import engine
from sqlalchemy import text

async def test():
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT 1"))
        print("Connected!", result.scalar())

asyncio.run(test())
```

---

## 5. ป้องกัน Inactive Pause (Free Tier)

Supabase free tier จะ **pause project อัตโนมัติถ้าไม่มี activity 1 สัปดาห์**

วิธีแก้: เพิ่ม health check endpoint และ cron job ping ทุกวัน

```python
# app/main.py
@app.get("/health")
async def health(db: AsyncSession = Depends(get_db)):
    await db.execute(text("SELECT 1"))
    return {"status": "ok"}
```

หรือตั้ง cron job (Railway / GitHub Actions) ping `/health` ทุกเช้า

---

## 6. Checklist

- [ ] สร้าง Supabase project
- [ ] รัน SQL schema ครบทุกตาราง
- [ ] copy DATABASE_URL ใส่ `.env`
- [ ] ทดสอบ connection จาก FastAPI
- [ ] เพิ่ม `.env` ใน `.gitignore`
- [ ] ตั้ง health check + cron ping (optional แต่แนะนำ)

---

*Created: 2026-04-17 | Researcher Agent*
