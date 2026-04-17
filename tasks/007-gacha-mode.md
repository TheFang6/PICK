# 007 — Gacha Mode

**Phase:** 2 (Core Logic)
**Estimated Time:** 3-4 ชม.
**Dependencies:** 004

---

## 🎯 Goal

Gacha mode — reshuffle pool เพื่อสุ่ม 3 ร้านใหม่ (ไม่ call API ใหม่) + limit 5 ครั้ง/มื้อ

---

## ✅ Subtasks

### Pool Cache Management

- [ ] `app/services/session_pool.py`:
  - [ ] In-memory dict หรือ Redis `{session_id: {pool, gacha_count, expires_at}}`
  - [ ] `create_session(pool) -> session_id`
  - [ ] `get_session(session_id) -> {pool, gacha_count}`
  - [ ] `increment_gacha(session_id) -> new_count`
  - [ ] TTL: 2 ชม. (auto-expire)

### Gacha Logic

- [ ] `app/services/gacha.py`:
  - [ ] Function: `roll(session_id) -> {candidates, remaining_rolls}`
    - [ ] ตรวจ session exists + ไม่หมดเวลา
    - [ ] ตรวจ `gacha_count < 5`
    - [ ] Sample 3 ร้านใหม่จาก pool (exclude current 3?)
    - [ ] Increment counter
    - [ ] Return 3 ร้านใหม่
  - [ ] Throw `GachaLimitExceeded` ถ้าเกิน 5 ครั้ง
  - [ ] Throw `SessionExpired` ถ้า session หมดอายุ

### Exclude Previous Picks (Optional)

- [ ] Option A: เก็บ `previous_candidates` ใน session → exclude จาก sample
- [ ] Option B: อนุญาตซ้ำได้ (โชคเสี่ยง)
- [ ] แนะนำ Option A เพื่อ UX ดี

### API Endpoint

- [ ] `POST /gacha/{session_id}` → return `{candidates, remaining_rolls}`
- [ ] Error codes:
  - 404: session not found
  - 410: session expired
  - 429: rolls exceeded

### Integration with Recommendation

- [ ] Update `/recommend` response → include `session_id`, `gacha_count_remaining`
- [ ] Gacha เป็น follow-up call ของ recommend

---

## 📋 Acceptance Criteria

✅ Gacha roll สำเร็จ → return 3 ร้านใหม่ที่ต่างจากครั้งก่อน (ถ้า pool พอ)
✅ Roll 5 ครั้ง → ครั้งที่ 6 error 429
✅ Session expire 2 ชม → roll 7 error 410
✅ ไม่ call Google Maps API เลย (verify จาก network log)
✅ หลายทีมรัน concurrent ได้ (แต่ละ session แยกกัน)

---

## 📝 Technical Notes

### Session Storage
**POC:** In-memory `dict` ใน FastAPI app
- ข้อเสีย: หาย ถ้า app restart
- แต่ POC: demo-friendly, ทีมไม่ restart บ่อย

**Future:** Redis
- Persistence + share ได้ระหว่าง replicas
- TTL native

### Weighted Sampling
```python
import random

def weighted_sample(pool, k, exclude_ids=None):
    candidates = [r for r in pool if r.id not in (exclude_ids or set())]
    if len(candidates) <= k:
        return candidates  # ถ้าเหลือน้อย ก็เอาทั้งหมด
    weights = [r.score for r in candidates]
    return random.choices(candidates, weights=weights, k=k)
```

### Gacha "Low Pool" Warning
- ถ้า pool เหลือ < 6 ร้าน → inform user ก่อน roll
- "เหลือแค่ 5 ร้าน กดสุ่มต่ออาจจะได้ชุดเดิม"

### Reset Gacha Counter
- Counter reset เมื่อ session ใหม่ (วันใหม่, /lunch ใหม่)
- ไม่ carry over

## 🔗 Reference

- `design.md` → Key Decisions (Gacha limit 5)
- `design.md` → Gacha Mode section
- `next-feature.md` → Gacha Adjustable Limits (future)
