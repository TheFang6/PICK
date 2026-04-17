# 016 — Web History Page

**Phase:** 4 (Web App)
**Estimated Time:** 3-4 ชม.
**Dependencies:** 005, 014

---

## 🎯 Goal

หน้า web แสดงประวัติการกินข้าว — ของตัวเองและของทีม, filter by month

---

## ✅ Subtasks

### Page Layout

- [ ] Route: `/history`
- [ ] Auth required
- [ ] Tabs: "ของฉัน" | "ของทีม"
- [ ] Filter: เดือน (dropdown)

Layout:
```
┌───────────────────────────────┐
│  Lunch History                 │
├───────────────────────────────┤
│  [ของฉัน] [ของทีม]             │
│  เดือน: [เมษายน 2026 ▼]       │
├───────────────────────────────┤
│  17 เม.ย. (ศุกร์)              │
│  🍜 ส้มตำนัว                   │
│  👥 Tong, Mai, Pete (3 คน)    │
│  ⭐ 4.5 | 📍 500m              │
├───────────────────────────────┤
│  16 เม.ย. (พฤ)                │
│  🍚 ข้าวมันไก่ประตูน้ำ          │
│  👥 Tong, Pete (2 คน)         │
│  ⭐ 4.3 | 📍 800m              │
└───────────────────────────────┘
```

### Data Fetching

- [ ] Endpoint: `GET /history?month=2026-04&scope=self|team`
- [ ] Default: current month + scope=self
- [ ] React Query with month as cache key

### Tab Switch

- [ ] "ของฉัน" → entries ที่ current user อยู่ใน attendees
- [ ] "ของทีม" → all entries ของทีม
- [ ] URL sync: `?tab=self` / `?tab=team`

### Month Filter

- [ ] Dropdown เลือกเดือน
- [ ] Default: current month
- [ ] Previous 6 เดือน + current
- [ ] URL sync: `?month=2026-04`

### Entry Card

- [ ] Date header (17 เม.ย. 2026 ศุกร์)
- [ ] Restaurant name + icon ตาม type
- [ ] Attendees list (ชื่อ + จำนวน)
- [ ] Metadata: rating, distance
- [ ] Click → open detail dialog (optional)

### Entry Detail (Optional)

- [ ] Dialog with:
  - รูปร้าน (จาก Google Photos)
  - ที่อยู่ (vicinity)
  - ลิงก์ Google Maps
  - ปุ่ม "เพิ่ม Blacklist"
- [ ] POC: skip, แสดงแค่ card

### Empty State

- [ ] ถ้าไม่มีข้อมูลในเดือนนั้น → "ไม่มีประวัติในเดือนนี้"
- [ ] เดือนล่าสุดว่าง → "ทีมยังไม่ได้ใช้บอต 🤷"

### Summary Stats (Optional)

- [ ] ด้านบน: "เมษายน 2026: กินไปแล้ว 12 ร้าน, 18 วัน"
- [ ] POC: skip

### Export (Optional)

- [ ] ปุ่ม "📥 Export CSV"
- [ ] เก็บไว้ใน next-feature.md

---

## 📋 Acceptance Criteria

✅ Load history หน้า → แสดงเดือนปัจจุบัน default
✅ Switch tab self/team → data เปลี่ยน
✅ Month dropdown → load data เดือนที่เลือก
✅ Card แสดงข้อมูลครบ: date, restaurant, attendees, metadata
✅ Empty state แสดงถูกจังหวะ
✅ Mobile responsive

---

## 📝 Technical Notes

### Date Formatting
```typescript
import { format } from 'date-fns';
import { th } from 'date-fns/locale';

format(new Date(entry.date), 'd MMM (EEE)', { locale: th });
// → "17 เม.ย. (ศ.)"
```

### Query
```typescript
const { data } = useQuery({
  queryKey: ['history', tab, month],
  queryFn: () => api.get(`/history?scope=${tab}&month=${month}`).then(r => r.json())
});
```

### Group by Date
- Backend return array, frontend group by date (local)
- หรือ backend group ให้เลย (save frontend work)

### Performance
- Pagination สำคัญถ้าใช้ไปนาน (เดือนละ ~20 entries, 1 ปี = 240)
- POC: ดึงทีละเดือน พอ
- Future: virtual scrolling

## 🔗 Reference

- `design.md` → Phase 4 Web App
- `design.md` → Database Schema (`lunch_history`)
- Task 005 — History tracking
