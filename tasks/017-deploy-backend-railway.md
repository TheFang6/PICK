# 017 — Deploy Backend to Railway

**Phase:** 5 (Deploy)
**Estimated Time:** 3-4 ชม.
**Dependencies:** 001, 008

---

## 🎯 Goal

Deploy FastAPI backend + PostgreSQL บน Railway — มี public URL สำหรับ Telegram webhook + web frontend

---

## ✅ Subtasks

### Railway Project Setup

- [ ] สมัคร Railway account (https://railway.app)
- [ ] New Project → Deploy from GitHub repo
- [ ] เลือก repo + branch `main`
- [ ] Railway auto-detect Python → build
- [ ] ถ้าไม่ auto-detect → เพิ่ม `Procfile`:
  ```
  web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
  release: alembic upgrade head
  ```

### PostgreSQL Service

- [ ] Railway project → "+ New" → Database → PostgreSQL
- [ ] Railway ให้ `DATABASE_URL` อัตโนมัติ (postgresql://...)
- [ ] Link service → backend service (inject env var)

### Environment Variables

- [ ] Backend service → Variables:
  ```
  DATABASE_URL=${{Postgres.DATABASE_URL}}
  TELEGRAM_BOT_TOKEN=xxx
  GOOGLE_MAPS_API_KEY=xxx
  WEBHOOK_SECRET=random-uuid
  OFFICE_LAT=13.7563
  OFFICE_LNG=100.5018
  SEARCH_RADIUS_M=1000
  ENV=production
  ALLOWED_ORIGINS=https://pick.vercel.app,http://localhost:3000
  ```
- [ ] Generate `WEBHOOK_SECRET` = `openssl rand -hex 32`

### Build Configuration

- [ ] `requirements.txt` pinned versions
- [ ] `runtime.txt` (ถ้าต้อง): `python-3.11.8`
- [ ] Build command (auto): `pip install -r requirements.txt`
- [ ] Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

### Database Migration

- [ ] Release phase: `alembic upgrade head` (อยู่ใน Procfile)
- [ ] หรือ manual: Railway CLI
  ```bash
  railway run alembic upgrade head
  ```
- [ ] Verify: `railway connect Postgres` → `\dt` ดูตาราง

### Public Domain

- [ ] Backend service → Settings → Domains
- [ ] Generate Railway domain: `pick-backend.up.railway.app`
- [ ] (Optional) Custom domain: `api.pick.app`
- [ ] HTTPS auto-provision (Let's Encrypt)

### Telegram Webhook Setup

- [ ] Set webhook ไปยัง public URL:
  ```bash
  curl -F "url=https://pick-backend.up.railway.app/telegram/webhook" \
       -F "secret_token=${WEBHOOK_SECRET}" \
       https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setWebhook
  ```
- [ ] Verify:
  ```bash
  curl https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getWebhookInfo
  ```
- [ ] Response มี `"url"` + `"pending_update_count": 0`

### Health Check

- [ ] GET `/health` → 200 `{"status": "ok"}`
- [ ] Railway → Settings → Healthcheck Path: `/health`
- [ ] Railway auto-restart ถ้า unhealthy

### Logs & Monitoring

- [ ] Railway → Deployments → View Logs (realtime)
- [ ] Logs ไปยัง stdout (Python `logging` module)
- [ ] (Optional) Integrate Sentry: `sentry-sdk[fastapi]`

### CORS Configuration

- [ ] `app/main.py`:
  ```python
  from fastapi.middleware.cors import CORSMiddleware
  
  app.add_middleware(
      CORSMiddleware,
      allow_origins=os.getenv("ALLOWED_ORIGINS", "").split(","),
      allow_credentials=True,
      allow_methods=["*"],
      allow_headers=["*"],
  )
  ```

### Deployment Flow

- [ ] Git push → Railway auto-deploy
- [ ] Build logs → ดู error
- [ ] ถ้า fail → rollback ด้วยปุ่ม Redeploy previous

### Rate Limiting (Optional)

- [ ] `slowapi` middleware
- [ ] POC: skip — traffic น้อย

### Secret Management

- [ ] ห้าม commit `.env` (มี `.gitignore`)
- [ ] Railway variables encrypted at rest
- [ ] Rotate `WEBHOOK_SECRET` เป็นระยะ

---

## 📋 Acceptance Criteria

✅ `railway up` หรือ git push → deploy สำเร็จ
✅ `https://pick-backend.up.railway.app/health` → 200 OK
✅ Alembic migration run สำเร็จ (ตาราง users, restaurants, ... ครบ)
✅ Telegram webhook set สำเร็จ → pending_update_count = 0
✅ `/start` ใน Telegram → bot ตอบ (end-to-end)
✅ Logs แสดงชัดเจน — debug ได้
✅ Database backup enabled (Railway auto-backup)

---

## 📝 Technical Notes

### Railway Pricing (POC)
- Hobby plan: $5/mo (500 hours execution)
- Free tier: $5 credit/mo (พอสำหรับ POC)
- PostgreSQL: $5/mo (1GB storage)

### Database Connection Pool
```python
# app/database.py
engine = create_async_engine(
    DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,  # reconnect if dropped
)
```

### Graceful Shutdown
```python
@app.on_event("shutdown")
async def shutdown():
    await engine.dispose()
```

### Scheduled Jobs (Attendance Reset)
- ใช้ APScheduler หรือ Railway Cron
- Railway Cron: ~ "0 0 * * *" → call reset endpoint
- POC: APScheduler ภายใน FastAPI ก็พอ

### Backup Strategy
- Railway PostgreSQL auto-backup daily (keep 7 days)
- (Optional) Export weekly → S3

## 🔗 Reference

- `design.md` → Phase 5 Deploy
- Railway docs: https://docs.railway.app
