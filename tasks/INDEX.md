# PICK (Food) — Task Breakdown

**Scope:** Full POC (Must + Should + Could)
**Timeline:** ~10 วัน full-time
**Reference:** `../design.md`

---

## 📋 Task List

### Phase 1 — Foundation (2-3 วัน)

- [x] [001 — Project Setup](./001-project-setup.md)
- [x] [002 — Google Maps Integration](./002-google-maps-integration.md)
- [x] [003 — Restaurants Schema & CRUD](./003-restaurants-schema-crud.md)

### Phase 2 — Core Logic (2-3 วัน)

- [x] [004 — Recommendation Pipeline](./004-recommendation-pipeline.md)
- [x] [005 — History Tracking](./005-history-tracking.md)
- [x] [006 — Blacklist System](./006-blacklist-system.md)
- [x] [007 — Gacha Mode](./007-gacha-mode.md)

### Phase 3 — Telegram Bot (2-3 วัน)

- [x] [008 — Telegram Bot Foundation](./008-telegram-bot-foundation.md)
- [x] [009 — Attendance System](./009-attendance-system.md)
- [x] [010 — Lunch & Poll Flow](./010-lunch-poll-flow.md)
- [x] [011 — Gacha Bot Integration](./011-gacha-bot-integration.md)
- [ ] [012 — Blacklist Commands](./012-blacklist-commands.md)
- [ ] [013 — Manual Restaurant Commands](./013-manual-restaurant-commands.md)

### Phase 4 — Web App (1-2 วัน)

- [ ] [014 — Web Project Setup](./014-web-project-setup.md)
- [ ] [015 — Web Blacklist Page](./015-web-blacklist-page.md)
- [ ] [016 — Web History Page](./016-web-history-page.md)

### Phase 5 — Deploy (1 วัน)

- [ ] [017 — Deploy Backend to Railway](./017-deploy-backend-railway.md)
- [ ] [018 — Deploy Frontend to Vercel](./018-deploy-frontend-vercel.md)
- [ ] [019 — End-to-End Testing](./019-e2e-testing.md)

---

## 🗺️ Dependency Graph

```
001 ─┬─▶ 002 ─┐
     │       ├─▶ 004 ─▶ 005 ─▶ 006 ─▶ 007
     └─▶ 003 ─┘                       │
                                      ▼
              008 ─▶ 009 ─▶ 010 ─▶ 011 ─▶ 012 ─▶ 013
                                      │
                                      ▼
                             014 ─▶ 015 ─▶ 016
                                      │
                                      ▼
                             017 ─▶ 018 ─▶ 019
```

---

## 📊 Status Summary

- Total: 19 tasks
- Done: 11
- In Progress: 0
- Blocked: 0

Update status ด้วยการเปลี่ยน `[ ]` → `[x]` ใน checklist ด้านบน
