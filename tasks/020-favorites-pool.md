# 020 — Favorites Pool

**Phase:** 3.5 (Enhancement)
**Estimated Time:** 2-3 ชม.
**Dependencies:** 003, 004, 008

---

## 🎯 Goal

เพิ่มระบบ "ร้านประจำ" ที่ทีมไปกินบ่อย — ร้านใน pool มีโอกาสถูกเลือกสูงกว่าร้านทั่วไป 2 เท่า โดย blacklist ยังมี priority สูงสุด

---

## ✅ Subtasks

### Model — `FavoriteRestaurant`

- [ ] สร้าง `app/models/favorite.py`
  ```python
  class FavoriteRestaurant(Base):
      __tablename__ = "user_favorites"
      id: UUID (pk)
      user_id: UUID (FK → users.id)
      restaurant_id: UUID (FK → restaurants.id)
      created_at: DateTime
      # UniqueConstraint(user_id, restaurant_id)
  ```
- [ ] เพิ่ม import ใน `app/models/__init__.py`
- [ ] สร้าง Alembic migration

### Service — `favorite_repo.py`

- [ ] `add_favorite(db, user_id, restaurant_id)` → upsert
- [ ] `remove_favorite(db, user_id, restaurant_id)` → delete
- [ ] `list_favorites(db, user_id)` → list[Restaurant]
- [ ] `get_favorite_restaurant_ids(db, user_ids)` → set[UUID]
  - Union semantics เหมือน blacklist — ดึง favorites ของทุกคนในทีมรวมกัน

### แก้ Recommendation Pipeline

- [ ] แก้ `recommend()` ใน `app/services/recommendation.py`:
  1. ดึง `favorite_ids = favorite_repo.get_favorite_restaurant_ids(db, user_ids)`
  2. ส่งเข้า context: `"favorite_ids": favorite_ids`
- [ ] แก้ `score_restaurants()`:
  - ถ้า `r.id in favorite_ids` → score *= 2.0 (weight 2x)
  - Blacklist ถูกตัดออกก่อนหน้า (`filter_restaurants`) จึงไม่มี conflict

### Priority Order

```
filter_restaurants():
  1. ตัด blacklist (permanent + today) ← ชนะเสมอ
  2. ตัด recently visited (7 วัน)
  3. ตัด closed/out-of-radius

score_restaurants():
  4. คำนวณ score ปกติ
  5. ร้านใน favorites → score *= 2.0 ← boost ตรงนี้
```

### Bot Handler — `/pool`

- [ ] สร้าง `app/bot/handlers/pool_handler.py`
- [ ] `/pool add` → พิมพ์ชื่อร้าน → fuzzy search → เลือกจาก inline keyboard → save
- [ ] `/pool remove` → แสดง list favorites → เลือกลบ
- [ ] `/pool list` → แสดงร้านทั้งหมดใน pool ของ user
- [ ] Callback data prefixes: `pool_add:`, `pool_rm:`

### Message Formats

```
/pool list:
⭐ ร้านประจำของคุณ (3 ร้าน)

1. ตำสวย
2. ผัดไทยพระยา
3. สเต็กแซนต้า

/pool add ตำสวย:
✅ เพิ่ม "ตำสวย" เข้าร้านประจำแล้ว

/pool remove:
[ตำสวย] [ผัดไทย] [สเต็ก]
เลือกร้านที่ต้องการลบ
```

### Register Handlers

- [ ] เพิ่มใน `app/bot/application.py`
- [ ] เพิ่มใน `run_polling.py`

---

## 📋 Acceptance Criteria

✅ `/pool add <ชื่อ>` → search + เลือก + save ลง DB
✅ `/pool list` → แสดงร้านประจำ
✅ `/pool remove` → inline keyboard เลือกลบ
✅ ร้านใน favorites มี score 2x ใน recommendation
✅ ร้านที่ถูก blacklist ไม่ปรากฏ แม้อยู่ใน favorites
✅ History penalty ยังทำงานปกติ (ร้าน fav ที่เพิ่งไป ไม่ถูก recommend ซ้ำ)
✅ Tests ครอบคลุม: favorite_repo CRUD, score boost, blacklist > favorites

---

## 📝 Technical Notes

### Blacklist vs Favorites Conflict

ไม่มี conflict จริงๆ เพราะ:
1. `filter_restaurants()` ตัด blacklist ออกก่อน
2. `score_restaurants()` ทำงานกับร้านที่ผ่าน filter แล้ว
3. ดังนั้น ร้านที่ถูก blacklist ไม่มีทางถูก boost

### History + Favorites Balance

- ร้าน A อยู่ใน favorites (+2x) แต่เพิ่งไปเมื่อวาน → ถูกตัดออกจาก `recent_restaurant_ids` (7 วัน)
- หลัง 7 วัน penalty หาย → ร้าน A กลับมามี 2x boost อีกครั้ง
- ผลลัพธ์: ร้านประจำไม่ถูก recommend ทุกวัน แต่มีโอกาสสูงกว่าปกติ

### ConversationHandler vs Inline Callback

ใช้ inline callback (เหมือน blacklist) แทน ConversationHandler:
- `/pool add ชื่อ` → search → แสดง inline keyboard
- ง่ายกว่า multi-step conversation
- ไม่มี state ค้าง

---

## 🔗 Reference

- `design.md` → Recommendation Pipeline
- Task 004 — Recommendation Pipeline
- Task 006 — Blacklist System (pattern เดียวกัน)
- Task 012 — Blacklist Commands (UX reference)
