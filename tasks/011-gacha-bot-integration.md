# 011 — Gacha Bot Integration

**Phase:** 3 (Telegram Bot)
**Estimated Time:** 3-4 ชม.
**Dependencies:** 007, 010

---

## 🎯 Goal

เชื่อม Gacha logic (task 007) กับ Telegram bot — ทั้งปุ่ม Gacha ในโพล และ `/gacha` standalone command

---

## ✅ Subtasks

### Gacha Button Handler (ใน Poll)

- [ ] Handler: `handle_gacha_callback(query)`
- [ ] Parse `callback_data` → extract `poll_id`
- [ ] Call `gacha.roll(session_id)` จาก task 007
- [ ] Error handling:
  - ถ้า `GachaLimitExceeded` → alert: "สุ่มครบ 5 ครั้งแล้ว ตัดสินใจซะที! 😤"
  - ถ้า `SessionExpired` → alert: "โพลหมดอายุแล้ว กรุณา /lunch ใหม่"
- [ ] ถ้าสำเร็จ:
  1. Update `poll_session.candidates` = ร้าน 3 ตัวใหม่
  2. Reset `poll_votes` (หรือไม่? decision point)
  3. Edit message → แสดงร้านใหม่ + `remaining_rolls`
  4. Update keyboard → ปุ่ม 3 ร้านใหม่

### Reset Votes Decision

- [ ] Option A: Reset votes ทุกครั้งที่ Gacha
  - Pro: ทีมได้โหวตใหม่
  - Con: คนที่โหวตไปแล้วต้องโหวตซ้ำ
- [ ] Option B: Keep votes
  - Pro: ถ้าใครโหวตไปแล้วยังอยู่
  - Con: votes map ไป restaurant_id เก่าที่ไม่อยู่ในลิสต์แล้ว → broken
- [ ] **แนะนำ Option A** — cleaner UX

### Message Update Format

```
🎲 Gacha! (สุ่ม 2/5)

🍽️ ร้านใหม่ 3 ร้าน
1️⃣ ตำสวย ⭐ 4.4 (600m)
2️⃣ ผัดไทยพระยา ⭐ 4.2 (700m)
3️⃣ สเต็กแซนต้า ⭐ 4.6 (900m)

[1️⃣ ตำสวย] [2️⃣ ผัดไทย] [3️⃣ สเต็ก]
[🎲 Gacha (เหลือ 3 ครั้ง)] [❌ ยกเลิก]
```

### `/gacha` Standalone Command

- [ ] Handler: `handlers/gacha_solo.py`
- [ ] Logic:
  1. Get user_id (1 คน เท่านั้น)
  2. รัน recommendation pipeline (reuse task 004) แต่ attendees = [current_user]
  3. สุ่ม 1 ร้าน (ไม่ใช่ 3)
  4. บันทึกเข้า history ทันที (ไม่มี poll)
  5. Reply: "วันนี้ไปร้านนี้เลยนะ 🎯\n\n🍜 ส้มตำนัว (500m, ⭐4.5)"

### Differences: Poll Gacha vs Solo Gacha

| Feature | Poll Gacha | Solo Gacha |
|---|---|---|
| Context | ทีมหลายคน | คนเดียว |
| Action | Reshuffle 3 ร้าน | สุ่ม 1 ร้านเลย |
| Vote | Yes (ต้องโหวต) | No (auto-pick) |
| History | หลัง timeout | ทันที |
| Limit | 5 ครั้ง/มื้อ | ไม่จำกัด |

---

## 📋 Acceptance Criteria

✅ ปุ่ม Gacha ใน poll ทำงาน → ร้านเปลี่ยน 3 ร้านใหม่
✅ Remaining count แสดงถูก (5 → 4 → 3 → 2 → 1)
✅ ครั้งที่ 6 → alert error ไม่ผ่าน
✅ `/gacha` standalone ได้ร้าน 1 ร้านทันที + บันทึก history
✅ กด Gacha หลังโหวตแล้ว → votes reset (Option A)

---

## 📝 Technical Notes

### Telegram `answer_callback_query`
- ต้อง call ทุก callback → ไม่งั้น loading spinner ติด
- `alert=True` → modal popup (ใช้กับ error)

### Edit vs New Message
- ใช้ `edit_message_text` + `edit_message_reply_markup`
- Vote count update inline
- ไม่ต้อง spam chat

### Performance
- Gacha ไม่ call Google Maps API → response ควร < 500ms
- Session cache ทำงาน (task 007) → instant

## 🔗 Reference

- `design.md` → Gacha Mode
- `design.md` → Poll System
- Task 007 — Gacha core logic
