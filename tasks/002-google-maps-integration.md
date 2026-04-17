# 002 — Google Maps Integration

**Phase:** 1 (Foundation)
**Estimated Time:** 4-6 ชม.
**Dependencies:** 001

---

## 🎯 Goal

เชื่อมต่อ Google Maps Places API (Nearby Search) — ดึงร้านอาหารรอบพิกัดออฟฟิศพร้อม metadata ที่จำเป็น

---

## ✅ Subtasks

### Google Cloud Setup

- [ ] สร้าง Google Cloud Project
- [ ] Enable Places API (New)
- [ ] สร้าง API key + restrict to backend IP (production)
- [ ] ใส่ `GOOGLE_MAPS_API_KEY` ใน `.env`
- [ ] Test API key ด้วย curl → confirm return 200 OK

### Service Layer

- [ ] สร้าง `app/services/google_maps.py`
- [ ] Function: `search_nearby(lat, lng, radius, type="restaurant") -> List[Restaurant]`
- [ ] Function: `get_photo_url(photo_reference, max_width=400) -> str`
- [ ] Parse response เป็น Pydantic schema:
  - `place_id`, `name`, `geometry.location`, `vicinity`
  - `rating`, `user_ratings_total`, `price_level`
  - `types`, `business_status`, `opening_hours.open_now`
  - `photos[0].photo_reference`

### Error Handling

- [ ] จัดการ quota exceeded → raise custom exception
- [ ] จัดการ network timeout → retry 1 ครั้ง
- [ ] Logging: log response status + request count
- [ ] Return empty list ถ้า `status != "OK"`

### Testing

- [ ] Unit test: mock `httpx` response → verify parser
- [ ] Integration test (optional): call จริง 1 ครั้ง → assert return ≥ 10 ร้าน
- [ ] API endpoint (dev only): `GET /dev/nearby?lat=X&lng=Y` → return ผลลัพธ์

---

## 📋 Acceptance Criteria

✅ Call Nearby Search → return ≥ 20 ร้าน (ในพื้นที่ปกติ)
✅ Parse ได้ทุก field ที่ระบุ
✅ Handle error ได้โดยไม่ crash (invalid key, quota exceed, network error)
✅ ใส่ API key ใน `.env` เท่านั้น (ไม่ hardcode)

---

## 📝 Technical Notes

### API Endpoint
```
GET https://maps.googleapis.com/maps/api/place/nearbysearch/json
    ?location={lat},{lng}
    &radius={meters}
    &type=restaurant
    &opennow=true
    &key={API_KEY}
```

### Photo URL Construction
```
https://maps.googleapis.com/maps/api/place/photo
    ?photoreference={ref}
    &maxwidth=400
    &key={API_KEY}
```

### Cost
- $0.032/request (Nearby Search)
- $200 free credit/เดือน → ~6,250 requests
- 132 requests/เดือน คาดการณ์ = ฟรี 100%

### Pagination (Future)
- Google ส่ง `next_page_token` ได้ max 60 ร้าน (3 pages)
- POC ใช้ page แรก (20 ร้าน) ก็พอ → ขยายได้ทีหลัง

## 🔗 Reference

- `design.md` → Google Maps API section
- `integrate-google-maps.md` → full API reference
