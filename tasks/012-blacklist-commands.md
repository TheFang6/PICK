# 012 — Blacklist Commands (Telegram)

**Phase:** 3 (Telegram Bot)
**Estimated Time:** 3-4 ชม.
**Dependencies:** 006, 008

---

## 🎯 Goal

เพิ่ม Telegram commands สำหรับจัดการ blacklist — add, list, remove ผ่าน bot

---

## ✅ Subtasks

### `/blacklist add <ชื่อร้าน>` Command

- [ ] Handler: `handlers/blacklist.py`
- [ ] Logic:
  1. Parse arg: ชื่อร้าน
  2. ค้นร้านใน DB:
     - ถ้าไม่เจอ → "ไม่เจอร้านชื่อนี้ครับ ลองพิมพ์ชื่อที่ตรงขึ้น"
     - ถ้าเจอหลายร้าน → แสดงลิสต์ให้เลือก (inline keyboard)
     - ถ้าเจอร้านเดียว → proceed
  3. ถามโหมด (inline keyboard):
     - [🚫 ถาวร]
     - [📅 แค่วันนี้]
     - [❌ ยกเลิก]
  4. Handle callback → add to blacklist (task 006)
  5. Reply confirm: "เพิ่ม 'ส้มตำนัว' เข้า blacklist (ถาวร) แล้วครับ ✅"

### `/blacklist list` Command

- [ ] Logic:
  1. Query `blacklist_repo.list(user_id)`
  2. Format message:
     ```
     🚫 Blacklist ของคุณ (5 ร้าน)

     ถาวร:
     • ร้านลาบอีสาน
     • ตำทะเลบ้านใน
     • หมูกระทะหลังออฟฟิศ

     วันนี้:
     • ส้มตำนัว
     • ข้าวมันไก่ประตูน้ำ

     /blacklist remove <ชื่อร้าน> เพื่อลบ
     ```

### `/blacklist remove <ชื่อร้าน>` Command

- [ ] Logic:
  1. Search ร้านใน blacklist ของ user
  2. ถ้าเจอ → remove
  3. Reply confirm

### Conversation Flow (Alternative)

- [ ] **Mode 1**: พิมพ์ `/blacklist add ส้มตำนัว` → bot ถามโหมด → add
- [ ] **Mode 2**: พิมพ์ `/blacklist` เฉย ๆ → bot แสดงเมนู
  ```
  จัดการ Blacklist
  [➕ เพิ่ม] [📋 ดูทั้งหมด] [❌ ปิด]
  ```

### Search Autocomplete (Optional)

- [ ] Use `InlineQueryHandler` — พิมพ์ `@PickBot ส้มตำ` → แสดงลิสต์ร้านให้เลือก
- [ ] POC: skip, ใช้ full match ก่อน

### Also Trigger from Poll

- [ ] ใน poll candidates (task 010): เพิ่มปุ่ม "❌ ไม่เอาร้านนี้"
- [ ] กด → bot ถาม: "Blacklist ถาวร หรือแค่วันนี้?"
- [ ] Add → remove ร้านออกจาก poll ทันที → auto-refill จาก pool

---

## 📋 Acceptance Criteria

✅ `/blacklist add X` สำเร็จ → ดูใน DB มี entry
✅ Add today → หลังเที่ยงคืนหายเอง (ตรวจใน recommendation)
✅ `/blacklist list` แสดงครบ แยก permanent/today
✅ `/blacklist remove X` ลบสำเร็จ
✅ Inline keyboard ทำงาน — กดปุ่มได้ไม่ error
✅ Blacklist entry affect recommendation ทันที (test: add → /lunch ใหม่ → ร้านนั้นไม่โผล่)

---

## 📝 Technical Notes

### Fuzzy Search
```python
# ใช้ PostgreSQL trigram extension
CREATE EXTENSION pg_trgm;
CREATE INDEX restaurants_name_trgm ON restaurants USING gin (name gin_trgm_ops);

# Query
SELECT * FROM restaurants
WHERE name % 'ส้มตำ'  # % = similar operator
ORDER BY similarity(name, 'ส้มตำ') DESC
LIMIT 5;
```

### Conversation State
- ใช้ `ConversationHandler` จาก python-telegram-bot
- States: `SEARCHING`, `CONFIRMING_MODE`, `DONE`
- User ไม่ตอบ → timeout 2 นาที

### Edge Cases
- Add ร้านซ้ำ → inform "มีใน blacklist อยู่แล้ว"
- Remove ร้านที่ไม่มีใน blacklist → "ไม่มีร้านนี้ใน blacklist"
- ชื่อร้านภาษาไทย + อังกฤษ → search ทั้ง 2 แบบ

## 🔗 Reference

- `design.md` → Blacklist Commands
- Task 006 — Blacklist core logic
