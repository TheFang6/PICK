# PICK — Next Features & Optimizations

เอกสารเก็บไอเดีย feature / optimization ที่ **ไม่เอาเข้า POC** — ไว้พิจารณาหลัง demo ทีม

---

## 🔄 Google Maps API — Cache Strategies

### ปัญหาที่แก้
Google Maps Nearby Search ให้ **~50 ร้านเดิม** แทบทุกวัน (ranked by prominence) → Cache ได้ดี แต่ทีมจะเจอร้านซ้ำ

### Options

**Option 1: Fetch ทุก `/lunch` (POC — ใช้ตัวนี้)**
- ง่าย, fresh data, cost ไม่สูง
- 132 requests/เดือน ฟรี ($200 credit)

**Option 2: Cache 24h + Pagination**
- Call API ครั้งแรกของวัน → cache 24 ชม.
- Pagination ดึงให้ครบ 60 ร้าน (Google จำกัดสูงสุด)
- Re-check `open_now` จาก `opening_hours` ที่เก็บไว้
- ลด API calls ~80%

**Option 3: Cache 7 วัน + Multi-query**
- Cache refresh รายสัปดาห์
- Query แยกหลาย type: thai, japanese, noodle, cafe ฯลฯ
- แต่ละ query: 50 ร้าน → รวม 200+ ร้านใน pool
- หลากหลายสุด แต่ implementation ซับซ้อนขึ้น

---

## 🎲 Restaurant Variety — วิธีเพิ่มความหลากหลาย

### ปัญหา
- Google Maps ในรัศมี 1 กม. → ~50 ร้าน
- History cooldown 7 วัน → หลังครบรอบกลับมาชุดเดิม
- ทีมจะบ่นว่า "วนร้านเดิม"

### Solutions

**1. Dynamic Radius**
- วันธรรมดา: 500m (ร้านใกล้)
- วันที่ pool เหลือน้อย: ขยาย → 1km → 2km
- Trigger: pool หลัง filter < N ร้าน

**2. Ranking Rotation**
- สลับใช้ `rankby=prominence` กับ `rankby=distance`
- แต่ละแบบให้ร้าน top-50 ต่างกัน
- รอบนี้ prominence รอบหน้า distance → ได้ร้านใหม่

**3. Multi-type Search**
- Query แยกทีละประเภท:
  - `thai_restaurant`
  - `japanese_restaurant`
  - `noodle_shop`
  - `cafe`
  - `restaurant` (general)
- รวมผล → pool 100-200+ ร้าน

**4. Manual Restaurants** ⭐ (สำคัญสุด)
- `/addrestaurant` → รถเข็น, โรงอาหาร, ร้านซอยเล็ก
- Google ไม่เจอ แต่เป็นร้านที่ทีมกินจริง
- Scale กับขนาดทีม — ยิ่งคนเยอะ ยิ่งหลากหลาย

**5. Seasonal / Context-aware**
- ฝนตก → ลดร้านที่ต้องเดินเยอะ
- ร้อนจัด → prioritize ร้านมีแอร์
- ต้องเก็บ metadata เพิ่ม (มีแอร์, in-door/out-door)

---

## ❤️ Favorites + Frequent (Option C)

### จาก design.md — Tier 3

**Favorites** (manual mark)
- User กด ❤️ ร้านโปรด
- **Boost weight** ใน recommendation → เจอบ่อยขึ้น
- `/favorite` shortcut — เรียกตรง ไม่ต้องรอ poll

**Frequent** (auto-detect)
- ระบบนับจาก history: กินเกิน X ครั้ง/สัปดาห์ = frequent
- **Penalty** (ลดน้ำหนัก) → กระจายให้ลองร้านใหม่

**แยก logic ชัดเจน:**
- "โปรด" = อยากให้เสนอ (user intent)
- "ประจำ" = กินบ่อยพอแล้ว (auto detection)

**POC ตัดสินใจ: ใช้ Option D (ไม่มี favorites)** — เรียบง่าย, ใช้แค่ history cooldown + manual add

---

## 🎲 Gacha — Adjustable Limits

### POC: Limit 3 ครั้ง/มื้อ
เหตุผล: decision fatigue + commit ไม่ใช่ save cost

### Future Options
- **Dynamic limit**: ทีมเล็ก (≤3 คน) → 5 ครั้ง, ทีมใหญ่ → 3 ครั้ง
- **Adaptive**: ถ้าทีมใช้เวลาโหวตเร็ว → เพิ่ม limit, ถ้าช้า → ลด
- **Unlimited mode**: toggle ใน group settings — ถ้าทีมพร้อมวน

---

## 📊 Advanced Features (Tier 3 — ต้องการ data สะสมก่อน)

### Post-meal Rating
- หลังกินเสร็จ Bot ถาม: "อร่อยไหม? ⭐⭐⭐⭐⭐"
- เก็บ rating ส่วนตัวต่อร้าน → override Google rating
- ใช้ personalize recommendation

### Mood-based
- `/lunch mood=spicy` / `mood=light` / `mood=comfort`
- Filter ตาม tag ร้าน
- ต้อง manual tag หรือใช้ LLM จาก description

### Budget Cap
- `/lunch budget=100` → filter ร้านราคาต่อหัว ≤ 100
- ต้องเก็บ price_per_person (ไม่ใช่แค่ price_level 0-4)

### Dietary Restriction
- Per-user: vegetarian, halal, เจ, no_beef
- Filter ใน recommendation pipeline

### Analytics Dashboard
- ทีมกินร้านไหนบ่อยสุด
- Blacklist rate ร้านไหนสูงสุด
- Weekly variety score
- Personal taste profile

---

## 🌐 Multi-location / Custom Location

### จาก design.md — Tier 2

**Custom Location Search**
- `/lunch near <ชื่อสถานที่>`
- Share location ผ่าน Telegram location feature
- ใช้ Google Geocoding API แปลงชื่อ → lat/lng
- Use case: ต้องไปทำธุระหลังกินข้าว (รอบสถานีรถไฟ ฯลฯ)

---

## 🎨 Web App Enhancements (Post-POC)

- Restaurant detail page (รีวิว, รูป, เมนู)
- Heatmap แสดงพื้นที่ที่กินบ่อย
- Export history → CSV
- Shareable recommendation link (สำหรับ guest ที่ไม่ได้อยู่ใน group)
- Multi-group support (บ้าง project, ทีม, office)

---

## 🤖 Bot UX Improvements

- Inline command suggestions
- Voice message → transcribe → search restaurant
- Photo message → OCR menu → suggest similar
- Natural language: "อยากกินเผ็ด ๆ ใกล้ ๆ" → parse → filter

---

## 📌 Priority Ranking (คาดการณ์)

หลัง POC ใช้จริง 1-2 สัปดาห์ คาดว่า pain point จะเรียงลำดับประมาณนี้:

1. **ร้านซ้ำบ่อย** → แก้ด้วย Multi-type Search หรือ Dynamic Radius
2. **อยากมี favorite** → implement Option C
3. **บางคนไม่ชอบเผ็ด** → Dietary restriction
4. **ประหยัด cost** → Cache 24h
5. **Analytics** → Dashboard

ค่อยดูจริงจากการใช้งาน ไม่ต้องเดา 🔍
