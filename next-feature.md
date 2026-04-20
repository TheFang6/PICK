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

## 🚨 Restaurant Closed / Out of Stock — Fallback System

### ปัญหา
หลังทีมโหวตเลือกร้านแล้ว และเดินทางไปถึงจริง ๆ อาจเจอเหตุการณ์:
- ร้าน**ปิดไม่ตามเวลา** (เจ้าของปิดเอง, วันหยุดพิเศษ, เจ้าของป่วย)
- **ของหมด / เมนูหมด** (โดยเฉพาะร้านขายดีช่วงเที่ยง)
- **คิวยาวเกินไป** (รอ >30 นาที)
- **ปิดปรับปรุง** (Google Maps ยังไม่ update)

ทีมต้องหาร้านใหม่ **เฉพาะหน้า** ขณะอยู่นอกออฟฟิศแล้ว — เครียด, เสียเวลา, อาจแยกย้ายกัน

---

### Option A: Fallback Backup Pool ⭐ (แนะนำ — ง่ายสุด)

**Concept:** ทุกครั้งที่ poll ปิด เก็บ **ร้านสำรอง 2-3 อันดับถัดไป** จาก candidate เดิมไว้ใน session

**Flow:**
```
Poll ปิด → ร้าน #1 (winner) + เก็บ #2, #3 เป็น backup ใน DB
     ↓
ทีมไปถึง → ร้านปิด
     ↓
คนใดคนหนึ่งพิมพ์ /fallback ใน Telegram
     ↓
Bot ส่ง inline button: "เปลี่ยนไป [ร้าน #2]" / "เปลี่ยนไป [ร้าน #3]"
     ↓
กดเลือก → update active_meal.restaurant_id → แจ้งทุกคนใน group
```

**Data model:**
```sql
ALTER TABLE active_meals ADD COLUMN backup_restaurant_ids INT[];
-- backup_restaurant_ids = [12, 34]  (ranking ลดหลั่นจาก poll result)
```

**ข้อดี:**
- ไม่ต้อง call API เพิ่ม — ใช้ข้อมูลที่มีแล้ว
- ทุกคนในทีมเห็นตัวเลือกเดียวกัน (consistent)
- ง่ายมาก (~2-3 ชม. implement)

**ข้อเสีย:**
- Backup อาจอยู่ไกลจากร้าน #1 (ถ้าทีมเดินไปแล้วต้องย้อนกลับ)
- ไม่รู้ว่า backup เปิดอยู่ไหม ณ เวลานั้น

---

### Option B: Re-Gacha On-site (Location-aware)

**Concept:** ใช้ Gacha เดิม แต่ **ส่ง location ปัจจุบัน** ไปด้วย → reshuffle โดย exclude ร้านที่เพิ่งไปมา

**Flow:**
```
ทีมอยู่ที่ร้านปิด → กดปุ่ม "📍 Share Location" ใน Telegram
     ↓
Bot รับ lat/lng → เรียก /regacha with current_location
     ↓
Backend:
  1. Load session pool เดิม (filter ไว้แล้วตั้งแต่ /lunch)
  2. Exclude ร้านปัจจุบัน + ร้านที่เพิ่ง reject
  3. Re-rank by distance จาก current_location (ไม่ใช่ออฟฟิศ)
  4. Return 3 ร้านใหม่ ใกล้จุดปัจจุบันที่สุด
     ↓
ส่ง poll แบบย่อให้ทีม (timeout 2 นาที)
```

**ข้อดี:**
- ได้ร้านที่ **ใกล้จุดปัจจุบัน** ไม่ใช่ใกล้ออฟฟิศ
- ใช้ infrastructure เดิม (session pool + Gacha) — ไม่เพิ่ม complexity มาก
- ทีมมีสิทธิเลือกร่วม (democratic)

**ข้อเสีย:**
- ต้อง maintain session pool นานกว่าเดิม (จนถึงกินเสร็จ, ไม่ใช่จบที่ poll)
- ถ้า pool เหลือน้อย อาจไม่มีร้านใกล้พอ

---

### Option C: Nearby Auto-suggest (Fresh API Call)

**Concept:** ปล่อยคนใดคนหนึ่งกดปุ่ม "ร้านปิด/หมด" → Bot call Google Maps **ด้วย location ปัจจุบัน**

**Flow:**
```
User กดปุ่ม "ร้านปิด 🚫" ใน meal card
     ↓
Bot ขอ location (auto ถ้าเคยให้สิทธิ์)
     ↓
Call Google Places API:
  - location = ตำแหน่งปัจจุบัน
  - radius = 300m (เดินได้ภายใน 5 นาที)
  - rankby = distance
  - open_now = true (Google filter ให้เลย)
  - keyword = ยังคงใช้ preference ทีม (optional)
     ↓
ได้ 10-20 ร้าน → filter blacklist ทีม → top 5
     ↓
ส่ง inline buttons — กดเลือกได้เลย (no poll, time-sensitive)
```

**ข้อดี:**
- **Real-time data** — Google บอก open_now ล่าสุด
- ไม่จำกัดด้วย session pool เดิม
- เหมาะกับสถานการณ์เฉพาะหน้า (เร่งด่วน)

**ข้อเสีย:**
- +1 API call/มื้อ (~30 requests/เดือน ถ้า ~10% meals เจอปัญหา)
- `open_now` จาก Google ไม่ 100% accurate (ยังอาจปิด physical)
- Skip democratic poll (ตัดสินใจเร็ว = คนเดียวกด)

---

### Hybrid Recommendation (ถ้าจะทำจริง)

**Combine A + C:**
1. **First tap "ร้านปิด":** โชว์ backup #2, #3 จาก Option A ก่อน (เร็ว, ไม่ใช้ API)
2. **ถ้ากด "ไม่เอา backup":** fallback ไป Option C (fresh nearby search)
3. **Optional:** หลังกินเสร็จ Bot ถาม "ร้าน [#1] ปิดจริงไหม?" → ถ้าใช่ mark `temporarily_closed=true` ใน DB 24 ชม.

---

### Data & Tracking

**เก็บ event เพื่อปรับปรุง:**
```sql
CREATE TABLE closed_events (
  id SERIAL PRIMARY KEY,
  meal_id INT REFERENCES active_meals(id),
  restaurant_id INT REFERENCES restaurants(id),
  reason VARCHAR(50),  -- 'closed', 'out_of_stock', 'long_queue', 'renovation'
  fallback_restaurant_id INT,
  fallback_option VARCHAR(10),  -- 'A', 'B', 'C'
  reported_at TIMESTAMP DEFAULT NOW()
);
```

**ประโยชน์:**
- ร้านไหนปิดบ่อย → auto-penalty ใน ranking
- `closing_note` ของ manual restaurant → อัปเดตแบบ community-driven
- Analytics: % meals ที่เจอปัญหา → ประเมินว่าควรทำ fallback จริงจังไหม

---

### Priority สำหรับ Phase ไหน?

**Phase 2.5 (หลัง POC demo):**
- ถ้าทีมใช้จริงแล้วเจอปัญหานี้ >2 ครั้ง/สัปดาห์ → implement **Option A** ก่อน (ง่ายสุด, ไม่เสียเงินเพิ่ม)

**Phase 3+ (ถ้ายังมี pain):**
- Upgrade ไป **Hybrid A+C** เมื่อมี data รองรับ

**ไม่แนะนำทำ Option B แยก:**
- ซ้อนกับ Option A เกินไป — ทำ Hybrid A+C ดีกว่า

---

### Implementation Estimate

| Option | Backend | Bot | Frontend | Total |
|--------|---------|-----|----------|-------|
| A (Backup) | 2 ชม. | 1 ชม. | - | ~3 ชม. |
| B (Re-gacha location) | 3 ชม. | 2 ชม. | - | ~5 ชม. |
| C (Fresh API) | 3 ชม. | 2 ชม. | - | ~5 ชม. |
| Hybrid A+C | 5 ชม. | 3 ชม. | - | ~8 ชม. |

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
