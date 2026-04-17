# 008 — Telegram Bot Foundation

**Phase:** 3 (Telegram Bot)
**Estimated Time:** 4-6 ชม.
**Dependencies:** 001, 003

---

## 🎯 Goal

Setup Telegram Bot — webhook, /start command, user registration, pairing token

---

## ✅ Subtasks

### Bot Registration

- [ ] สร้าง Bot ผ่าน @BotFather
- [ ] ตั้งชื่อ + username (e.g., `PickLunchBot`)
- [ ] Copy `BOT_TOKEN` → Railway env vars
- [ ] ตั้ง commands ผ่าน @BotFather:
  ```
  start - เริ่มใช้งาน
  lunch - สุ่มร้านอาหารเที่ยง
  gacha - สุ่มร้านเดี่ยว
  wfh - ประกาศ work from home วันนี้
  in - ประกาศเข้าออฟฟิศ
  blacklist - จัดการ blacklist
  addrestaurant - เพิ่มร้านที่ไม่มีใน Maps
  editrestaurant - แก้ไขร้านที่ตัวเองเพิ่ม
  help - ดูคำสั่งทั้งหมด
  ```

### Webhook Setup

- [ ] สร้าง `app/api/telegram.py` — FastAPI router
- [ ] Endpoint: `POST /webhook/telegram`
  - [ ] Parse update จาก Telegram
  - [ ] Validate secret token (Telegram feature)
  - [ ] Dispatch ไปยัง handler ที่เหมาะสม
- [ ] Script `setup_webhook.py`:
  - [ ] Call `setWebhook` API
  - [ ] Config secret token

### Bot Framework

- [ ] ใช้ `python-telegram-bot` v20+ (async)
- [ ] สร้าง `app/bot/` โฟลเดอร์:
  ```
  bot/
  ├── __init__.py
  ├── application.py   # Bot app setup
  ├── handlers/
  │   ├── start.py
  │   ├── lunch.py
  │   ├── attendance.py
  │   ├── blacklist.py
  │   └── restaurant.py
  └── utils/
      ├── keyboards.py  # Inline keyboard builders
      └── formatters.py # Message formatters
  ```

### `/start` Command

- [ ] Handler: `handlers/start.py`
- [ ] Logic:
  1. Extract `telegram_id`, `name` จาก update
  2. UPSERT user ใน DB:
     - ถ้ามีแล้ว → reply welcome back
     - ถ้าไม่มี → create + reply welcome + guide
  3. Generate pairing token (UUID, expire 10 min)
  4. Save token ใน table `pairing_tokens`
  5. Reply with inline button:
     ```
     สวัสดีครับ {name}! 👋
     เริ่มใช้งาน PICK ได้เลย

     [🌐 เปิดหน้า Web]
     ```
     URL: `https://pick.vercel.app/pair?token=xxx`

### Pairing Token Schema

- [ ] Model `app/models/pairing_token.py`:
  ```python
  pairing_tokens:
    id (UUID, PK)
    token (TEXT, UNIQUE)
    user_id (UUID, FK users)
    expires_at (TIMESTAMP)
    consumed_at (TIMESTAMP, NULLABLE)
    created_at (TIMESTAMP)
  ```
- [ ] Migration: `add_pairing_tokens`

### Error Handling

- [ ] ถ้า user reply ไม่ตรง command → "ไม่เข้าใจคำสั่งครับ พิมพ์ /help เพื่อดูคำสั่งทั้งหมด"
- [ ] Try/except wrap ทุก handler → log + reply "เกิดข้อผิดพลาด ลองใหม่อีกครั้ง"

---

## 📋 Acceptance Criteria

✅ Bot ตอบ /start ได้ภายใน 3 วินาที
✅ User ใหม่ถูก register ใน DB
✅ User เดิมใช้ /start ซ้ำ ไม่ duplicate
✅ Pairing link ทำงาน (ยังไม่ต้องทำ web page — task 014)
✅ Webhook ยืนยันสำเร็จผ่าน `getWebhookInfo`
✅ Invalid command → error message ชัดเจน

---

## 📝 Technical Notes

### Async Setup
```python
from telegram.ext import Application, CommandHandler

app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start_handler))
```

### Webhook vs Polling
- **Dev:** polling (ง่าย, local test)
- **Production:** webhook (realtime, ไม่กิน CPU)

### Secret Token
```python
# Telegram จะส่ง header: X-Telegram-Bot-Api-Secret-Token
# ใช้ตรวจว่าเป็น request จาก Telegram จริง
```

### Pairing Token Expiry
- 10 นาที = balance ระหว่าง security + UX
- ถ้า expire → user run `/start` ใหม่

## 🔗 Reference

- `design.md` → Telegram Bot commands
- `design.md` → Pairing Flow
