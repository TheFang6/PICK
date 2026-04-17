# 009 — Attendance System

**Phase:** 3 (Telegram Bot)
**Estimated Time:** 3-4 ชม.
**Dependencies:** 008

---

## 🎯 Goal

ระบบ attendance: /wfh, /in, auto-drop on timeout, query ใครเข้าออฟฟิศวันนี้

---

## ✅ Subtasks

### Schema

- [ ] Model `app/models/attendance.py`:
  ```python
  user_attendance:
    id (UUID, PK)
    user_id (UUID, FK users)
    date (DATE)
    status (ENUM: 'in_office' | 'wfh' | 'unknown')
    updated_at (TIMESTAMP)
    UNIQUE (user_id, date)
    INDEX (date, status)
  ```
- [ ] Migration: `add_user_attendance`

### Repository

- [ ] `app/services/attendance_repo.py`:
  - [ ] `set_status(user_id, status, date=today)` — UPSERT
  - [ ] `get_today_status(user_id) -> status`
  - [ ] `get_attendees(date, statuses=['in_office', 'unknown']) -> List[User]`
  - [ ] `drop_unknown(date)` — set unknown → wfh หลัง poll timeout

### Bot Handlers

- [ ] `/wfh` command:
  - [ ] Set status = 'wfh' สำหรับวันนี้
  - [ ] Reply: "รับทราบครับ พักผ่อนให้เต็มที่ 🏠"

- [ ] `/in` command:
  - [ ] Set status = 'in_office'
  - [ ] Reply: "รับทราบ! เจอกันที่ออฟฟิศ 🏢"

- [ ] `/status` command (optional):
  - [ ] Show สถานะของ user
  - [ ] Show ทีมวันนี้: "📊 วันนี้ (จันทร์ 17 เม.ย.)\n✅ ในออฟฟิศ: 4 คน\n🏠 WFH: 2 คน\n❓ ยังไม่กด: 0 คน"

### Auto-Detection Logic

- [ ] ถ้า user ยังไม่เคยกด /wfh หรือ /in วันนี้ → status = `unknown` (default)
- [ ] Endpoint: `GET /attendance/today` → list พร้อม status

### Integration with `/lunch` (task 010 จะใช้)

- [ ] Helper function: `get_todays_attendees()`
  - Return users with status in `['in_office', 'unknown']`
  - Used by `/lunch` เพื่อตัดสินใจว่าโพลหรือไม่

### Midnight Reset (Optional)

- [ ] ไม่ต้อง reset — แค่ insert ด้วย `date=today` ใหม่เป็นอัตโนมัติ
- [ ] Query default date = today → user วันนี้ไม่เคยกด = ไม่มี row = status `unknown`

---

## 📋 Acceptance Criteria

✅ /wfh ตั้ง status สำเร็จ → ดู /attendance/today เห็น 'wfh'
✅ /in ตั้ง status สำเร็จ
✅ UPSERT ถูกต้อง — กด /wfh แล้วเปลี่ยน /in → status เปลี่ยน
✅ Attendees query return รายชื่อถูกต้อง (in_office + unknown)
✅ ข้าววันต้องแยกกัน — วันที่ต่างกัน status ไม่ชนกัน

---

## 📝 Technical Notes

### Timezone
- ใช้ Asia/Bangkok (UTC+7)
- `today = datetime.now(tz=BKK_TZ).date()`
- Store as DATE (ไม่ใช่ TIMESTAMP) → ตัด time ออก

### UPSERT Pattern (SQLAlchemy)
```python
from sqlalchemy.dialects.postgresql import insert

stmt = insert(UserAttendance).values(
    user_id=user_id, date=today, status=status
).on_conflict_do_update(
    index_elements=['user_id', 'date'],
    set_={'status': status, 'updated_at': now}
)
```

### Unknown Handling
- `unknown` = user ที่ยังไม่กดอะไร
- Include ใน poll (optimistic: assume อยู่ office)
- Drop เมื่อ poll timeout (ไม่ได้โหวต = WFH จริง)

## 🔗 Reference

- `design.md` → Attendance section
- `design.md` → Smart Attendance + Poll Threshold
