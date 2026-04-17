# 005 — History Tracking

**Phase:** 2 (Core Logic)
**Estimated Time:** 3-4 ชม.
**Dependencies:** 003, 004

---

## 🎯 Goal

บันทึกประวัติการกินข้าว + integrate เป็น filter ใน recommendation pipeline (กันซ้ำ 7 วัน)

---

## ✅ Subtasks

### Schema

- [ ] สร้าง model `app/models/lunch_history.py`:
  ```python
  lunch_history:
    id (UUID, PK)
    restaurant_id (UUID, FK restaurants)
    date (DATE)
    attendees (JSONB, array of user_ids)
    created_at (TIMESTAMP)
    INDEX (date)
    INDEX (restaurant_id)
  ```

- [ ] Migration: `add_lunch_history`
- [ ] Apply migration ✅

### Repository

- [ ] `app/services/history_repo.py`:
  - [ ] `log_lunch(restaurant_id, attendees, date=today)`
  - [ ] `get_recent_restaurant_ids(user_ids, days=7) -> Set[UUID]`
  - [ ] `get_user_history(user_id, limit=30) -> List[LunchHistoryEntry]`
  - [ ] `get_team_history(limit=30) -> List[LunchHistoryEntry]`

### Integration with Recommendation

- [ ] Update `filter_restaurants` (task 004):
  - [ ] Get `recent_ids = history_repo.get_recent_restaurant_ids(attendees, 7)`
  - [ ] Exclude ร้านที่ `restaurant.id in recent_ids`
- [ ] Add `log_lunch()` call หลัง poll timeout (task 010 จะใช้)

### API Endpoints

- [ ] `GET /history` — query params: `user_id`, `limit`, `offset`
- [ ] `GET /history/team` — recent team lunches
- [ ] `POST /history` — manual log (dev only)

---

## 📋 Acceptance Criteria

✅ Log entry → ดูได้ทั้งจาก user history และ team history
✅ Recommendation filter ออก ร้านที่ทีมเพิ่งกินใน 7 วัน
✅ Performance OK — query history ไม่เกิน 100ms
✅ Attendees เก็บเป็น JSONB array (ไม่ใช่ relation table — ง่ายกว่าสำหรับ POC)

---

## 📝 Technical Notes

### Filter Logic (รวมกับทีม)
```python
# ถ้ามี 3 คน A, B, C in_office วันนี้
# และ B เพิ่งกินร้าน X เมื่อวาน
# → X ถูก exclude (ไม่ fair แต่ simple)
```

**ทำไมใช้ "เพิ่มคน" เป็น union ไม่ใช่ intersection?**
- Union: ร้านที่ **ใครคนใดคนนึง**เพิ่งกิน = exclude
- Intersection: ร้านที่ **ทุกคน**เพิ่งกิน = exclude (น้อยมาก)
- POC เลือก union เพราะปกติทีมกินพร้อมกัน — ถ้าเพิ่งกิน 1 คน แสดงว่าทั้งทีมเพิ่งกิน

**Edge case:** WFH user เมื่อวานไปกินคนเดียว → วันนี้เข้า office → ไม่ควร block
- Future: filter เฉพาะ entries ที่ user นั้นอยู่ใน `attendees`
- POC: accept trade-off

### Rolling Window
- 7 วัน = default
- Future: configurable per team

### JSONB vs Junction Table
- JSONB: 1 write, fast read, ไม่ต้อง join
- Junction table (`lunch_attendees`): normalized, query complex analytics ง่ายกว่า
- POC: JSONB — Analytics เป็น Tier 3 อยู่แล้ว

## 🔗 Reference

- `design.md` → Database Schema (`lunch_history`)
- `design.md` → Recommendation Pipeline (History filter)
