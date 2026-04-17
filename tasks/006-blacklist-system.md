# 006 — Blacklist System

**Phase:** 2 (Core Logic)
**Estimated Time:** 4-5 ชม.
**Dependencies:** 003, 004

---

## 🎯 Goal

ระบบ blacklist 2 โหมด (permanent + today-only) — filter ร้านที่ user ไม่อยากกินออกจาก recommendation

---

## ✅ Subtasks

### Schema

- [ ] สร้าง model `app/models/user_blacklist.py`:
  ```python
  user_blacklist:
    id (UUID, PK)
    user_id (UUID, FK users)
    restaurant_id (UUID, FK restaurants)
    mode (ENUM: 'permanent' | 'today')
    expires_at (TIMESTAMP, NULLABLE)  # ใช้เฉพาะ mode=today
    created_at (TIMESTAMP)
    UNIQUE (user_id, restaurant_id)
    INDEX (user_id)
    INDEX (expires_at)  # สำหรับ cleanup
  ```

- [ ] Migration: `add_user_blacklist`

### Repository

- [ ] `app/services/blacklist_repo.py`:
  - [ ] `add(user_id, restaurant_id, mode='permanent')`
    - ถ้า mode='today' → set `expires_at = today 23:59:59`
  - [ ] `remove(user_id, restaurant_id)`
  - [ ] `list(user_id) -> List[BlacklistEntry]`
  - [ ] `get_blacklisted_restaurant_ids(user_ids) -> Set[UUID]`
    - รวม permanent + unexpired today blacklist
  - [ ] `cleanup_expired()` — ลบ entries ที่ `expires_at < now()`

### Integration with Recommendation

- [ ] Update `filter_restaurants` (task 004):
  - [ ] Get `blacklisted_ids = blacklist_repo.get_blacklisted_restaurant_ids(attendees)`
  - [ ] Exclude ร้านที่ `restaurant.id in blacklisted_ids`

### Cleanup Job

- [ ] Background task (APScheduler): run `cleanup_expired()` ทุกเที่ยงคืน
- [ ] หรือ soft approach: query filter `expires_at IS NULL OR expires_at > now()`

### API Endpoints

- [ ] `POST /blacklist` — body: `{restaurant_id, mode}`
- [ ] `DELETE /blacklist/{id}` — remove from blacklist
- [ ] `GET /blacklist` — list ของ user ตัวเอง (auth required)

---

## 📋 Acceptance Criteria

✅ เพิ่ม blacklist permanent → filter ออกจาก recommendation ตลอด
✅ เพิ่ม blacklist today → filter ออกเฉพาะวันนี้ พรุ่งนี้กลับมา
✅ UNIQUE constraint ไม่ให้ add ซ้ำ
✅ User อื่นดู blacklist ของคนอื่นไม่ได้
✅ Cleanup job (หรือ query filter) ทำงาน — expired entries ไม่กวน

---

## 📝 Technical Notes

### Query for active blacklists
```sql
SELECT restaurant_id FROM user_blacklist
WHERE user_id = ANY(:user_ids)
  AND (expires_at IS NULL OR expires_at > now())
```

### Union Semantics (เหมือน History)
- ใครคนนึงใน team in_office blacklist ร้านไหน → exclude ทั้งหมด
- "Safer" decision — ไม่เสี่ยงเสนอร้านที่ใครไม่กิน

### Mode Auto-expire
- `mode='today'` + `expires_at = today 23:59:59 Asia/Bangkok`
- Cleanup: nightly job หรือ filter at query time
- Cleanup แนะนำเพราะ keep DB เล็ก

### Migration from Today → Permanent
- User ใช้ today-mode บ่อย ๆ กับร้านเดิม → ถามว่าอยาก upgrade เป็น permanent ไหม?
- Future feature, ไม่ต้องทำตอน POC

## 🔗 Reference

- `design.md` → Database Schema (`user_blacklist`)
- `design.md` → Blacklist 2 Modes section
