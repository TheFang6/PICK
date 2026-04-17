# 010 — Lunch & Poll Flow

**Phase:** 3 (Telegram Bot)
**Estimated Time:** 8-10 ชม.
**Dependencies:** 004, 005, 006, 008, 009

---

## 🎯 Goal

สร้าง `/lunch` command → ดึง attendees → รัน recommendation pipeline → เปิด poll ใน Telegram group → รับ vote → auto-pick winner on timeout

---

## ✅ Subtasks

### Schema

- [ ] Model `poll_session`:
  ```python
  poll_session:
    id (UUID, PK)
    chat_id (TEXT)
    message_id (INT)
    candidates (JSONB, array of restaurant_ids)
    session_id (TEXT)  # สำหรับ gacha pool cache
    status (ENUM: 'active' | 'completed' | 'cancelled')
    winner_restaurant_id (UUID, FK restaurants, NULLABLE)
    created_by (UUID, FK users)
    expires_at (TIMESTAMP)
    completed_at (TIMESTAMP, NULLABLE)
  ```

- [ ] Model `poll_votes`:
  ```python
  poll_votes:
    id (UUID, PK)
    poll_session_id (UUID, FK poll_session)
    user_id (UUID, FK users)
    restaurant_id (UUID, FK restaurants)
    created_at (TIMESTAMP)
    UNIQUE (poll_session_id, user_id)  # 1 vote/user/poll
  ```

- [ ] Migrations + apply ✅

### `/lunch` Handler

- [ ] `handlers/lunch.py`
- [ ] Logic:
  1. ดึง attendees จาก task 009: `get_attendees(today)`
  2. Threshold check:
     - 0 คน → "ไม่มีใครอยู่ออฟฟิศวันนี้เลย 😐"
     - 1 คน → skip poll, เสนอ 3 ร้านพร้อมปุ่ม "เลือกเลย"
     - ≥ 2 คน → proceed to poll
  3. Call `recommendation.recommend(attendee_ids, office_location)`
  4. สร้าง message + inline keyboard
  5. Save `poll_session` + `message_id`
  6. Schedule timeout job (10 นาที)

### Poll Message Format

```
🍽️ มื้อเที่ยงวันนี้ (17 เม.ย. 2026)
⏱️ โหวตภายใน 10 นาที | กำลังโหวต 0/4

1️⃣ ส้มตำนัว ⭐ 4.5 (500m)
2️⃣ ข้าวมันไก่ประตูน้ำ ⭐ 4.3 (800m)
3️⃣ ราเมง Ichiran ⭐ 4.7 (1km)

[1️⃣ ส้มตำ] [2️⃣ ข้าวมันไก่] [3️⃣ ราเมง]
[🎲 Gacha!] [❌ ยกเลิก]
```

### Vote Callback

- [ ] Handler: `handle_vote_callback(query)`
- [ ] Parse `callback_data` → extract poll_id, restaurant_id
- [ ] Validate user is in attendees list
- [ ] UPSERT `poll_votes` (1 vote/user/poll)
- [ ] Update message with vote counts (edit message)
- [ ] Handle edge case: กดซ้ำ = เปลี่ยน vote

### Cancel Button

- [ ] Handler: `handle_cancel_callback(query)`
- [ ] Only creator of poll สามารถยกเลิก
- [ ] Set `status = 'cancelled'`
- [ ] Edit message: "โพลถูกยกเลิก ❌"

### Timeout Handler (Background Job)

- [ ] APScheduler job: check polls with `expires_at < now()` + `status = 'active'`
- [ ] รันทุก 1 นาที
- [ ] สำหรับแต่ละ poll:
  1. Query votes → นับคะแนน
  2. ถ้าเสมอ → random pick
  3. ถ้าไม่มีใครโหวต → auto-pick อันดับ 1
  4. Set `status = 'completed'` + `winner_restaurant_id`
  5. Edit poll message:
     ```
     🎉 ผลโหวต
     ✅ Winner: ส้มตำนัว (2 votes)

     เจอกันที่ร้านครับ! 📍
     ```
  6. บันทึก `lunch_history.log_lunch(winner_id, voters)`
  7. Drop unknown users → wfh (optional)

### Threshold Logic Detail

- [ ] สำหรับ 1 คน case:
  - ส่ง message + 3 ปุ่ม
  - ไม่มี timeout
  - User กดปุ่ม → log ทันที

---

## 📋 Acceptance Criteria

✅ `/lunch` → bot ตอบภายใน 5 วินาที (รวม Maps API call)
✅ Inline keyboard กดได้ 5 ปุ่ม (3 ร้าน + gacha + cancel)
✅ Vote → message update แสดง count realtime
✅ Timeout 10 นาที → auto-pick winner
✅ Winner บันทึกเข้า history ทันที
✅ ไม่มี double vote (กดซ้ำ = เปลี่ยน)
✅ Threshold ทำงาน: 0/1/≥2 คน ต่างกันชัดเจน

---

## 📝 Technical Notes

### Callback Data Format
```
vote:{poll_id}:{restaurant_id}
gacha:{poll_id}
cancel:{poll_id}
```

### Concurrent Vote Handling
- Use DB transaction + UNIQUE constraint
- ถ้า conflict → UPSERT (user change vote)

### Timeout Implementation Options

**Option A: APScheduler (แนะนำ POC)**
- In-process scheduler
- พอสำหรับ ทีม 6 คน

**Option B: Celery + Redis**
- Robust, scale ได้
- Overkill สำหรับ POC

**Option C: DB polling**
- Cron ทุก 1 นาที query expired polls
- Simple, stateless

### Winner Announcement Edge Cases
- ✅ Single voter → เลือกตามโหวต
- ✅ Tie → random ระหว่างร้านที่คะแนนเท่ากัน
- ✅ No votes → auto-pick ลำดับ 1 (score สูงสุด)
- ✅ Cancelled → ไม่มี winner

## 🔗 Reference

- `design.md` → Phase 3 Telegram Bot
- `design.md` → Poll System
- `design.md` → Smart Attendance + Poll Threshold
