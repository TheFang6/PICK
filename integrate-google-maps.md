# Google Maps Places API Integration — PICK (Food)

> Setup Google Maps Places API สำหรับค้นหาร้านอาหารรอบออฟฟิศ

---

## 1. สร้าง Google Cloud Project

1. ไปที่ [cloud.google.com](https://cloud.google.com) → Sign in
2. คลิก **Select a project** → **New Project**
3. ตั้งชื่อ: `pick-food` → Create

---

## 2. เปิดใช้ Places API

1. ไปที่ **APIs & Services → Library**
2. ค้นหา `Places API` → คลิก **Enable**
3. (แนะนำ) เปิดเพิ่ม `Maps JavaScript API` ถ้าจะทำ Web map ทีหลัง

---

## 3. สร้าง API Key

1. **APIs & Services → Credentials → Create Credentials → API Key**
2. ได้ key เช่น `AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX`

### จำกัด Key (สำคัญมาก)

คลิก key ที่สร้าง → แก้ไข:

- **Application restrictions** → IP addresses
  - ใส่ IP ของ Railway server (หาได้จาก Railway dashboard)
- **API restrictions** → Restrict key → เลือก `Places API` เท่านั้น

> ⚠️ ถ้าไม่จำกัด key ใครก็ขโมยไปใช้ได้ทำให้เสียค่าใช้จ่ายโดยไม่รู้ตัว

---

## 4. เก็บ Key ใน .env

```env
GOOGLE_MAPS_API_KEY=AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
OFFICE_LAT=13.7563  # พิกัดออฟฟิศ (latitude)
OFFICE_LNG=100.5018 # พิกัดออฟฟิศ (longitude)
SEARCH_RADIUS_METERS=500  # รัศมีค้นหา (เมตร)
```

---

## 5. API ที่ใช้ใน Project

### Nearby Search — หาร้านรอบออฟฟิศ

```
GET https://maps.googleapis.com/maps/api/place/nearbysearch/json
    ?location={lat},{lng}
    &radius={meters}
    &type=restaurant
    &opennow=true        ← filter เฉพาะร้านที่เปิดอยู่
    &key={API_KEY}
```

Response ที่สำคัญ:
```json
{
  "results": [
    {
      "place_id": "ChIJ...",
      "name": "ร้านอาหาร A",
      "geometry": { "location": { "lat": 13.75, "lng": 100.50 } },
      "price_level": 2,        // 1=ถูก, 2=ปานกลาง, 3=แพง, 4=แพงมาก
      "opening_hours": { "open_now": true },
      "rating": 4.2
    }
  ]
}
```

### Place Details — ดูรายละเอียดเพิ่ม (optional)

```
GET https://maps.googleapis.com/maps/api/place/details/json
    ?place_id={place_id}
    &fields=name,opening_hours,price_level
    &key={API_KEY}
```

---

## 6. FastAPI Integration

```bash
pip install googlemaps
```

สร้างไฟล์ `app/services/maps.py`:

```python
import googlemaps
import os
from math import radians, sin, cos, sqrt, atan2

gmaps = googlemaps.Client(key=os.getenv("GOOGLE_MAPS_API_KEY"))

OFFICE_LAT = float(os.getenv("OFFICE_LAT"))
OFFICE_LNG = float(os.getenv("OFFICE_LNG"))
RADIUS = int(os.getenv("SEARCH_RADIUS_METERS", 500))

def haversine_km(lat1, lng1, lat2, lng2) -> float:
    R = 6371
    dlat = radians(lat2 - lat1)
    dlng = radians(lng2 - lng1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng/2)**2
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))

def get_nearby_restaurants(open_now: bool = True) -> list[dict]:
    results = gmaps.places_nearby(
        location=(OFFICE_LAT, OFFICE_LNG),
        radius=RADIUS,
        type="restaurant",
        open_now=open_now,
    )
    restaurants = []
    for r in results.get("results", []):
        loc = r["geometry"]["location"]
        restaurants.append({
            "source": "google_maps",
            "google_place_id": r["place_id"],
            "name": r["name"],
            "lat": loc["lat"],
            "lng": loc["lng"],
            "price_level": r.get("price_level"),
            "distance_km": haversine_km(OFFICE_LAT, OFFICE_LNG, loc["lat"], loc["lng"]),
            "open_now": r.get("opening_hours", {}).get("open_now", True),
        })
    return restaurants
```

---

## 7. Price Level → ราคา (บาท)

```python
PRICE_LEVEL_MAP = {
    1: "~50฿",
    2: "~100฿",
    3: "~200฿",
    4: "300฿+",
    None: "ไม่ระบุ",
}
```

---

## 8. ค่าใช้จ่าย

Google ให้ **$200 free credit/เดือน** สำหรับ Maps Platform

| API | ราคาต่อ request | $200 ได้กี่ครั้ง |
|---|---|---|
| Nearby Search | $0.032 | ~6,250 ครั้ง |
| Place Details | $0.017 | ~11,760 ครั้ง |

**ประมาณการใช้งาน project นี้:**

```
ทีม 6 คน × 1 ครั้ง/วัน × 22 วันทำการ/เดือน
= ~132 Nearby Search requests/เดือน
= $4.22/เดือน → อยู่ใน free credit สบาย
```

ใช้ free credit ได้นาน **~47 เดือน** ถ้าใช้แค่ Nearby Search ครับ

---

## 9. Checklist

- [ ] สร้าง Google Cloud project
- [ ] เปิด Places API
- [ ] สร้าง API key + จำกัด IP และ API
- [ ] เพิ่ม GOOGLE_MAPS_API_KEY ใน .env
- [ ] ตั้งค่า OFFICE_LAT / OFFICE_LNG
- [ ] ทดสอบ Nearby Search
- [ ] ตรวจสอบ price_level mapping

---

*Created: 2026-04-17 | Researcher Agent*
