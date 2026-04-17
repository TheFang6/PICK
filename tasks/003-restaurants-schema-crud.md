# 003 — Restaurants Schema & CRUD

**Phase:** 1 (Foundation)
**Estimated Time:** 4-6 ชม.
**Dependencies:** 001, 002

---

## 🎯 Goal

สร้าง database schema + CRUD endpoints สำหรับร้านอาหาร (รองรับทั้ง Google Maps และ Manual)

---

## ✅ Subtasks

### Database Models

- [ ] สร้าง `app/models/user.py`:
  ```python
  users:
    id (UUID, PK)
    telegram_id (TEXT, UNIQUE)
    name (TEXT)
    created_at (TIMESTAMP)
  ```

- [ ] สร้าง `app/models/restaurant.py`:
  ```python
  restaurants:
    id (UUID, PK)
    place_id (TEXT, UNIQUE, NULLABLE)  # null = manual
    name (TEXT)
    source (ENUM: 'google_maps' | 'manual')
    lat (FLOAT, NULLABLE)
    lng (FLOAT, NULLABLE)
    vicinity (TEXT)
    rating (FLOAT)
    price_level (INT)
    types (JSONB)
    photo_reference (TEXT)
    closed_weekdays (JSONB, array of int 0-6)
    closed_monthly_ranges (JSONB, array of {start, end})
    added_by (UUID, FK users, NULLABLE)
    last_fetched_at (TIMESTAMP)
    created_at (TIMESTAMP)
  ```

### Migrations

- [ ] Create Alembic migration: `add_users_restaurants`
- [ ] Run migration locally ✅
- [ ] Verify tables + indexes ใน Railway PostgreSQL

### Repository Layer

- [ ] `app/services/restaurant_repo.py`:
  - [ ] `upsert_from_maps(data)` — UPSERT by place_id
  - [ ] `create_manual(data, user_id)` — source='manual'
  - [ ] `get_by_id(id)`
  - [ ] `list_all(filters)` — paginated
  - [ ] `update(id, data)`
  - [ ] `delete(id)` — soft delete (optional)

### API Endpoints

- [ ] `GET /restaurants` — list ทั้งหมด + filter by source
- [ ] `GET /restaurants/{id}` — detail
- [ ] `POST /restaurants/manual` — เพิ่มร้าน manual (auth required)
- [ ] `PUT /restaurants/{id}` — edit (เฉพาะร้าน manual + เจ้าของเอง)
- [ ] `DELETE /restaurants/{id}` — delete (เฉพาะร้าน manual + เจ้าของเอง)
- [ ] `POST /restaurants/sync-from-maps` — dev endpoint trigger sync

### Seed Data (Optional but useful)

- [ ] Script: seed 5 ร้าน manual สำหรับ test
- [ ] Script: call Maps API 1 ครั้ง → populate 20 ร้าน → save to DB

---

## 📋 Acceptance Criteria

✅ Migration apply สำเร็จ — ตาราง `users`, `restaurants` ครบ field
✅ UPSERT ทำงาน — call Maps API 2 ครั้ง ไม่ create ซ้ำ
✅ CRUD manual restaurant ทำงานครบ
✅ List endpoint รองรับ filter by `source`
✅ Auth check: user อื่นแก้ไขร้าน manual ของคนอื่นไม่ได้

---

## 📝 Technical Notes

- `place_id` เป็น unique key สำคัญ → UPSERT ใช้ตัวนี้
- Manual restaurants: `place_id = NULL`, `source = 'manual'`
- `closed_weekdays`: `[0, 6]` = ปิดจันทร์, เสาร์ (0=Mon, 6=Sun ISO-style หรือเลือกตาม Python weekday)
- `closed_monthly_ranges`: `[{"start": "2026-04-20", "end": "2026-04-25"}]` สำหรับร้านที่ปิดเฉพาะช่วง
- ใช้ UUID เพื่อ scalability — ไม่ collision ตอน merge data
- Index: `(source)`, `(place_id)`, `(added_by)`

## 🔗 Reference

- `design.md` → Database Schema section
- `design.md` → Restaurant Data Model (Hybrid)
