# 004 — Recommendation Pipeline

**Phase:** 2 (Core Logic)
**Estimated Time:** 6-8 ชม.
**Dependencies:** 002, 003

---

## 🎯 Goal

สร้าง recommendation engine 5 stages ที่เอาร้านจาก Maps + Manual → filter → score → เสนอ 3 ร้าน

---

## ✅ Subtasks

### Stage 1: Fetch

- [ ] สร้าง `app/services/recommendation.py`
- [ ] Function: `fetch_candidates(office_lat, office_lng, radius=1000)`
  - [ ] Call Google Maps (service จาก task 002)
  - [ ] UPSERT ลง DB (service จาก task 003)
  - [ ] Return combined list (Maps + Manual)

### Stage 2: Filter

- [ ] Function: `filter_restaurants(candidates, context)`
  - [ ] Filter `open_now = true` (ใช้ field จาก Maps, ถ้า manual ดูจาก `closed_weekdays`)
  - [ ] Filter distance ≤ radius (เฉพาะ Maps, manual ไม่มี lat/lng อาจผ่าน)
  - [ ] Filter `business_status != 'CLOSED_PERMANENTLY'`
  - [ ] Return filtered list

- [ ] Input `context` contains:
  - `today_weekday`
  - `today_date`
  - `attendees` (list of user_ids)

### Stage 3: Score

- [ ] Function: `score_restaurants(restaurants, context)`
  - [ ] Score component:
    - Rating × `user_ratings_total` (เชื่อถือได้ + ดัง)
    - Distance (ใกล้ = score สูงกว่า)
    - Price level (optional weight)
  - [ ] Weighted sum → `final_score`
  - [ ] Return sorted list

### Stage 4: Select Pool

- [ ] Function: `select_pool(scored, pool_size=10)`
  - [ ] Top N ร้านจาก score
  - [ ] Return as "session pool"

### Stage 5: Sample

- [ ] Function: `sample_candidates(pool, k=3)`
  - [ ] Random sample 3 ร้านจาก pool
  - [ ] Weight by score (r weighted sampling)
  - [ ] Return 3 ร้าน

### Integration

- [ ] Function: `recommend(user_ids, office_location) -> RecommendationResult`
  - [ ] รัน pipeline ครบ 5 stages
  - [ ] Return: `{candidates: [3 ร้าน], pool: [10 ร้าน], session_id}`
  - [ ] Cache `pool` ใน memory (Redis หรือ in-memory dict สำหรับ POC)

### API Endpoint

- [ ] `POST /recommend` → body: `{user_ids: [], location: {lat, lng}}`
- [ ] Response: `{candidates, pool, session_id}`
- [ ] Error: ไม่มี user in_office → 400

---

## 📋 Acceptance Criteria

✅ Pipeline ทำงานครบ 5 stages โดยไม่ crash
✅ Return 3 ร้านที่ไม่ซ้ำกัน
✅ Pool ≥ 5 ร้าน (ถ้า API ให้มาพอ)
✅ Filter ทำงาน — ร้านปิดไม่โผล่
✅ Score consistent — รันหลายรอบได้ลำดับ pool เดียวกัน

---

## 📝 Technical Notes

### Score Formula (เบื้องต้น)
```python
score = (
    (rating or 3.5) * 0.4 +
    log1p(user_ratings_total) * 0.3 +
    (1 - distance/max_distance) * 0.2 +
    normalize(price_level) * 0.1
)
```

### Pool Caching
- POC: in-memory dict `{session_id: pool}`
- Future: Redis หรือ DB table
- TTL: 2 ชม. (หมดเวลาโหวต + Gacha)

### Note ยังไม่รวม Blacklist & History
ขั้นนี้ filter เฉพาะ open_now + distance + business_status
Blacklist (task 006) และ History (task 005) จะเพิ่มเป็น filter เพิ่ม

## 🔗 Reference

- `design.md` → Recommendation Pipeline 5 Stages section
