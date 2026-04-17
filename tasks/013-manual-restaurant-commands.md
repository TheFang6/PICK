# 013 — Manual Restaurant Commands

**Phase:** 3 (Telegram Bot)
**Estimated Time:** 4-6 ชม.
**Dependencies:** 003, 008

---

## 🎯 Goal

เพิ่ม Telegram commands `/addrestaurant` และ `/editrestaurant` — รองรับการเพิ่มร้านที่ Google Maps ไม่มี (รถเข็น, โรงอาหาร, ร้านในซอย)

---

## ✅ Subtasks

### `/addrestaurant` Command

- [ ] Handler: `handlers/restaurant.py`
- [ ] Use `ConversationHandler` (multi-step):

**Flow:**
1. User: `/addrestaurant`
2. Bot: "ชื่อร้านอะไรครับ?"
3. User: "ลูกชิ้นปลาปู่"
4. Bot: "ราคาต่อจานประมาณเท่าไหร่? (ไม่ใส่ก็ได้)"
5. User: "60"
6. Bot: "ประเภทร้าน? (เช่น ก๋วยเตี๋ยว, ข้าวแกง, อื่น ๆ)"
7. User: "ก๋วยเตี๋ยว"
8. Bot: "ร้านนี้ปิดวันไหนบ้าง? (กด /skip ถ้าไม่แน่ใจ)"
9. User: เลือกจาก inline keyboard (จันทร์, อังคาร, ..., อาทิตย์) หรือ /skip
10. Bot confirm: "ยืนยันเพิ่มร้าน?\n- ชื่อ: ลูกชิ้นปลาปู่\n- ราคา: 60 บาท\n- ประเภท: ก๋วยเตี๋ยว\n\n[✅ ยืนยัน] [❌ ยกเลิก]"
11. User ยืนยัน → save + confirm

### `/editrestaurant` Command

- [ ] Use `ConversationHandler`:

**Flow:**
1. User: `/editrestaurant`
2. Bot: แสดงลิสต์ร้านที่ user เพิ่ม:
   ```
   เลือกร้านที่จะแก้ไข:
   1️⃣ ลูกชิ้นปลาปู่
   2️⃣ ข้าวแกงป้าแดง
   3️⃣ กาแฟเต่า
   [❌ ยกเลิก]
   ```
3. User เลือก → bot แสดงข้อมูลปัจจุบัน + เมนูแก้ไข:
   ```
   ลูกชิ้นปลาปู่
   - ราคา: 60 บาท
   - ประเภท: ก๋วยเตี๋ยว
   - วันหยุด: -

   [✏️ ชื่อ] [💰 ราคา] [🍜 ประเภท]
   [📅 วันหยุด] [🗓️ ปิดเดือน] [🗑️ ลบร้าน]
   [❌ ปิด]
   ```
4. User เลือกปุ่ม → bot ถาม input → update

### Closed Weekdays UI

- [ ] Inline keyboard แบบ multi-select:
  ```
  [✅ จันทร์] [❌ อังคาร] [❌ พุธ]
  [❌ พฤหัส] [❌ ศุกร์] [❌ เสาร์]
  [❌ อาทิตย์]
  [💾 บันทึก]
  ```
- [ ] กดแต่ละวัน → toggle ✅/❌
- [ ] กดบันทึก → update DB

### Closed Monthly Ranges (Optional UI)

- [ ] รูปแบบ: `YYYY-MM-DD ถึง YYYY-MM-DD`
- [ ] User พิมพ์: "2026-04-20 ถึง 2026-04-25"
- [ ] Parse → append to `closed_monthly_ranges` array

### Permission

- [ ] ร้านที่แก้ไขได้ = `added_by = current_user_id`
- [ ] Edit ร้านคนอื่น → reply "แก้ได้เฉพาะร้านที่คุณเพิ่มเองเท่านั้น"

### Delete Confirmation

- [ ] กด 🗑️ ลบ → bot confirm "แน่ใจนะครับ? ร้านนี้จะถูกลบถาวร [✅ ลบ] [❌ ยกเลิก]"
- [ ] ยืนยัน → soft delete (set `deleted_at`) หรือ hard delete
- [ ] POC: hard delete ก็ได้

---

## 📋 Acceptance Criteria

✅ `/addrestaurant` flow ทำงานครบ — ร้านเข้า DB สำเร็จ (`source='manual'`)
✅ `/editrestaurant` ดู list ร้านของตัวเอง + แก้ field ได้
✅ Closed weekdays toggle ใน keyboard — save สำเร็จ
✅ ร้าน manual โผล่ใน `/lunch` (รวมกับร้าน Maps)
✅ User แก้ไขร้านคนอื่นไม่ได้ (permission check)
✅ ยกเลิก flow ระหว่างทาง → ไม่มี garbage data

---

## 📝 Technical Notes

### ConversationHandler States
```python
from enum import Enum, auto

class AddState(Enum):
    NAME = auto()
    PRICE = auto()
    CATEGORY = auto()
    CLOSED_DAYS = auto()
    CONFIRM = auto()
```

### Timeout
- Conversation timeout 5 นาที
- ถ้า user ไม่ตอบ → cancel + reply "เวลาหมด กรุณาเริ่มใหม่"

### Validation
- ราคา: ต้องเป็นตัวเลข, > 0
- ชื่อร้าน: ไม่ว่าง, < 100 ตัวอักษร
- Duplicate name warning: "มีร้านชื่อคล้ายกันใน DB แล้ว (ตำสวย) — เพิ่มต่อไหม?"

### Inline Keyboard Multi-Select Pattern
```python
# Store state ใน callback_data หรือ user_data
# Toggle: call edit_message_reply_markup + rebuild keyboard
```

## 🔗 Reference

- `design.md` → Manual Restaurant Management
- `design.md` → Restaurant Data Model (Hybrid)
- Task 003 — Restaurants CRUD
