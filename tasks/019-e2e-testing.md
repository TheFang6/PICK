# 019 — End-to-End Testing

**Phase:** 5 (Deploy)
**Estimated Time:** 4-6 ชม.
**Dependencies:** 017, 018 (ทุก task ก่อนหน้า)

---

## 🎯 Goal

ทดสอบ flow จริงทั้งหมดบน production — จาก `/start` ถึง `/lunch` ถึง history page

---

## ✅ Subtasks

### Pre-Test Setup

- [ ] สร้าง Telegram test group (ใส่ bot + 3-4 tester)
- [ ] เตรียม tester: Tong, Mai, Pete (+ ตัวเอง)
- [ ] Reset DB (ถ้าจำเป็น) — fresh state
- [ ] ตรวจ env vars ครบ (bot token, maps key, webhook secret)

### Test 1: Pairing Flow

- [ ] User พิมพ์ `/start` ใน DM bot
- [ ] Bot reply ลิงก์ `https://pick.vercel.app/pair?token=xxx`
- [ ] Click ลิงก์ → browser เปิด → redirect ไป `/blacklist`
- [ ] Cookie session set แล้ว (DevTools → Application → Cookies)
- [ ] Refresh page → ยัง login อยู่
- [ ] Token ใช้ซ้ำ → error "token ใช้ไปแล้ว"

### Test 2: Attendance System

- [ ] User A พิมพ์ `/wfh` → bot confirm + save attendance
- [ ] User B พิมพ์ `/in` → bot confirm
- [ ] User C ไม่ตอบ (simulate timeout)
- [ ] ใช้ `/status` → เห็น A=WFH, B=IN, C=pending
- [ ] (ถ้ามี) Timeout 30 นาที → C auto-drop

### Test 3: Lunch Recommendation Flow

- [ ] User พิมพ์ `/lunch` ในกรุ๊ป
- [ ] Bot แสดงโพลรายชื่อร้าน 3-5 ร้าน (inline keyboard)
- [ ] ตรวจ: แต่ละร้านมี rating + distance
- [ ] ร้านไม่ซ้ำกับ `history` 30 วัน
- [ ] Blacklist (ของใครก็ได้) ไม่โผล่ใน poll
- [ ] ร้านปิดวันนี้ไม่โผล่ (check closed_weekdays)

### Test 4: Vote Flow

- [ ] User แต่ละคนกดโหวตร้าน
- [ ] Count vote แสดง realtime
- [ ] ร้านชนะ (majority) → bot announce
- [ ] Save to `lunch_history` — ตรวจ DB
- [ ] Attendees record ครบ

### Test 5: Gacha Mode

- [ ] User พิมพ์ `/gacha`
- [ ] Bot แสดงร้านใหม่ (reshuffle session pool)
- [ ] Gacha count = 1/5
- [ ] กดต่ออีก 4 ครั้ง → 5/5
- [ ] ครั้งที่ 6 → bot reject "reached limit"
- [ ] ร้าน Gacha ไม่ซ้ำร้านที่โชว์ไปแล้วในรอบนี้

### Test 6: Blacklist Commands

- [ ] User `/blacklist add ส้มตำนัว` → ถามโหมด → เลือก "ถาวร" → success
- [ ] User `/blacklist list` → เห็น "ส้มตำนัว"
- [ ] `/lunch` → ร้านนี้ไม่โผล่ในโพล
- [ ] User `/blacklist remove ส้มตำนัว` → หายจากลิสต์

### Test 7: Today Blacklist

- [ ] User `/blacklist add <ร้าน>` → เลือก "วันนี้"
- [ ] `/lunch` วันนี้ → ร้านไม่โผล่
- [ ] (Mock) เปลี่ยนวันที่เป็น +1 day → ร้านกลับมา
- [ ] หรือ test โดยตรง: query DB + filter logic

### Test 8: Manual Restaurant Add

- [ ] User `/addrestaurant` → flow ครบ
- [ ] ใส่ชื่อ, ราคา, ประเภท, วันหยุด → confirm
- [ ] ตรวจ DB: `source='manual'`
- [ ] `/lunch` ใน attendees เดียวกัน → ร้านนี้มีโอกาสโผล่

### Test 9: Edit Restaurant

- [ ] User `/editrestaurant` → เลือกร้านของตัวเอง
- [ ] แก้ราคา → save
- [ ] ตรวจ DB update
- [ ] User อื่นพยายาม edit ร้านของเรา → reject

### Test 10: Web — Blacklist Page

- [ ] เปิด `/blacklist` → เห็น list ทั้งหมด
- [ ] Search "ส้มตำ" → ผลการค้นหาแสดง
- [ ] กดเพิ่ม → dialog เลือก mode → confirm → refresh
- [ ] กดลบ → confirmation → remove สำเร็จ

### Test 11: Web — History Page

- [ ] เปิด `/history` → เห็นประวัติเดือนปัจจุบัน
- [ ] Tab "ของฉัน" → filter correct
- [ ] Tab "ของทีม" → แสดงทั้งหมด
- [ ] เปลี่ยนเดือน → load data เดือนเก่า
- [ ] Empty month → empty state แสดง

### Test 12: Mobile Responsive

- [ ] ทดสอบบน iPhone (Safari)
- [ ] ทดสอบบน Android (Chrome)
- [ ] หน้าจอแนวตั้ง + แนวนอน
- [ ] Font size อ่านง่าย
- [ ] ปุ่มกดได้ไม่พลาด (≥ 44x44px)

### Test 13: Edge Cases

- [ ] Attendance = 0 คน → `/lunch` → bot reply "ยังไม่มีใครมา"
- [ ] Attendance = 1 คน → `/lunch` → bot reply (แสดงร้านคนเดียว?)
- [ ] No restaurants in radius → "ไม่เจอร้านแถวนี้"
- [ ] Google Maps API down → fallback หรือ error message
- [ ] DB down → 503 + retry

### Test 14: Security

- [ ] Webhook endpoint requires `X-Telegram-Bot-Api-Secret-Token`
- [ ] Without secret → 403
- [ ] Session cookie HttpOnly (JavaScript read ไม่ได้)
- [ ] HTTPS enforced — HTTP redirect 301
- [ ] CORS origins restricted (ไม่ใช่ `*`)

### Test 15: Performance

- [ ] `/lunch` response time < 3 วินาที (first call, hit Maps API)
- [ ] `/lunch` response time < 1 วินาที (cached pool)
- [ ] Web page load < 2 วินาที (Lighthouse)
- [ ] DB query < 500ms (check pg_stat_statements)

---

## 📋 Acceptance Criteria

✅ Flow ทั้งหมด 15 tests ผ่าน
✅ Pairing → blacklist → lunch → history ใช้งานได้สบาย
✅ Mobile experience ดี
✅ Bug list บันทึกใน issue tracker (GitHub Issues)
✅ ระบบเสถียร 1 สัปดาห์ (no crash, no memory leak)
✅ User feedback จากทีม → collect + prioritize

---

## 📝 Technical Notes

### Test Group Setup
- Telegram group "PICK Test"
- Members: bot + 3-4 testers
- Timezone: UTC+7 (Asia/Bangkok)

### Automated Tests (Future)
- Playwright สำหรับ web E2E
- Pytest + httpx สำหรับ API integration
- POC: manual testing พอ

### Monitoring Checklist
- Railway logs → check errors daily
- Vercel logs → check web errors
- DB: `SELECT count(*) FROM lunch_history;` → ดู usage

### Rollback Plan
- Backend broken: Railway → Redeploy previous
- Frontend broken: Vercel → Promote previous deploy
- DB migration broken: `alembic downgrade -1`
- Data corruption: restore from daily backup

### Post-Launch
- Week 1: ใช้ทุกวัน ดู pattern
- Week 2: Collect feedback + bug list
- Week 3: Prioritize next-feature.md items
- Week 4: Iterate

### Feedback Channels
- Telegram group แยก: "PICK Feedback"
- หรือ `/feedback <msg>` command ใน bot
- Log ใน GitHub Issues

## 🔗 Reference

- `design.md` → POC Scope
- `next-feature.md` → backlog items สำหรับ iterate ต่อ
- All task files 001-018
