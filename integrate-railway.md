# Railway Integration Guide — PICK (Food)

> Deploy FastAPI backend + PostgreSQL ทั้งหมดบน Railway

---

## 1. สร้าง Railway Account & Project

1. ไปที่ [railway.app](https://railway.app) → Sign in ด้วย GitHub
2. คลิก **New Project**
3. เลือก **Deploy from GitHub repo** → เลือก repo ของ project

---

## 2. เพิ่ม PostgreSQL

1. ใน project dashboard คลิก **+ Add Service → Database → PostgreSQL**
2. Railway สร้าง Postgres instance ให้อัตโนมัติ
3. คลิก PostgreSQL service → แท็บ **Variables** → copy `DATABASE_URL`

หน้าตา DATABASE_URL:
```
postgresql://postgres:password@monorail.proxy.rlwy.net:PORT/railway
```

---

## 3. รัน Database Schema

เชื่อมต่อผ่าน Railway CLI:

```bash
# ติดตั้ง Railway CLI
npm install -g @railway/cli

# Login
railway login

# เชื่อมต่อ DB แล้วรัน SQL
railway connect PostgreSQL
```

หรือใช้ psql โดยตรง:
```bash
psql $DATABASE_URL -f schema.sql
```

SQL schema ใช้ไฟล์เดียวกับ integrate-supabase.md (ส่วน SQL schema)

---

## 4. ตั้งค่า Environment Variables

ใน Railway project → แท็บ **Variables** ของ FastAPI service → เพิ่ม:

```env
DATABASE_URL=${{PostgreSQL.DATABASE_URL}}   # reference จาก PostgreSQL service
TELEGRAM_BOT_TOKEN=...
GOOGLE_MAPS_API_KEY=...
OFFICE_LAT=13.7563
OFFICE_LNG=100.5018
```

> Railway รองรับ `${{SERVICE.VARIABLE}}` reference อัตโนมัติ ไม่ต้อง copy value เอง

---

## 5. Deploy FastAPI

สร้าง `Procfile` หรือ `railway.toml` ใน root:

```toml
# railway.toml
[deploy]
startCommand = "uvicorn app.main:app --host 0.0.0.0 --port $PORT"
```

Push code → Railway auto-deploy ทันที

---

## 6. ได้ Public URL

Railway ให้ URL อัตโนมัติ เช่น:
```
https://pick-food-production.up.railway.app
```

ใช้เป็น Telegram webhook:
```
https://pick-food-production.up.railway.app/telegram/webhook
```

---

## 7. ตั้ง Telegram Webhook

รันครั้งเดียวหลัง deploy:
```bash
curl "https://api.telegram.org/bot{TOKEN}/setWebhook?url=https://pick-food-production.up.railway.app/telegram/webhook"
```

---

## 8. ค่าใช้จ่าย

Railway free tier: **$5 credit/เดือน**

| Service | ราคา (ประมาณ) |
|---|---|
| FastAPI (512MB RAM) | ~$3/เดือน |
| PostgreSQL (1GB) | ~$2/เดือน |
| รวม | ~$5/เดือน |

**สำหรับ POC ทีม 6 คน ใช้ free credit ได้พอดีครับ**

ถ้าต้องการแน่ใจ plan paid เริ่มที่ $20/เดือน (ไม่ sleep, uptime สูงขึ้น)

---

## 9. Checklist

- [ ] สร้าง Railway project จาก GitHub repo
- [ ] เพิ่ม PostgreSQL service
- [ ] copy DATABASE_URL ไปตั้งใน Variables
- [ ] รัน SQL schema บน Railway Postgres
- [ ] ตั้ง environment variables ทั้งหมด
- [ ] Deploy FastAPI → ได้ public URL
- [ ] ตั้ง Telegram webhook URL
- [ ] ทดสอบ end-to-end

---

*Created: 2026-04-17 | Researcher Agent*
