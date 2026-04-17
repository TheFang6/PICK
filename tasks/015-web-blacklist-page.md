# 015 — Web Blacklist Page

**Phase:** 4 (Web App)
**Estimated Time:** 4-6 ชม.
**Dependencies:** 006, 014

---

## 🎯 Goal

สร้างหน้า web สำหรับจัดการ blacklist — ค้นหาร้าน, เพิ่ม/ลบ, สลับโหมด (permanent/today)

---

## ✅ Subtasks

### Page Layout

- [ ] Route: `/blacklist`
- [ ] Auth required (redirect to `/` ถ้าไม่มี session)
- [ ] Layout:
  ```
  ┌─────────────────────────────┐
  │  Blacklist                   │
  ├─────────────────────────────┤
  │  🔍 [ค้นหาร้าน...            ] │
  │                              │
  │  ผลการค้นหา:                  │
  │  □ ส้มตำนัว                  │
  │  □ ข้าวมันไก่                 │
  │                              │
  │  [+ เพิ่ม Blacklist]          │
  │                              │
  ├─────────────────────────────┤
  │  Blacklist ของคุณ (5 ร้าน)    │
  │                              │
  │  🚫 ร้านลาบอีสาน [ถาวร] [ลบ] │
  │  🚫 ตำทะเลบ้านใน [ถาวร] [ลบ] │
  │  🚫 ส้มตำนัว    [วันนี้][ลบ] │
  └─────────────────────────────┘
  ```

### Search Functionality

- [ ] Search input with debounce (300ms)
- [ ] Call `GET /restaurants?search={q}` → list ร้าน
- [ ] Display: name + rating + distance + source badge (📍 Maps / ✋ Manual)
- [ ] Click ร้าน → open dialog เลือก mode

### Add Blacklist Dialog

- [ ] Dialog component (shadcn):
  ```
  เพิ่ม "ส้มตำนัว" เข้า blacklist
  ─────────────────────────────
  เลือกโหมด:
  ( ) ถาวร — ไม่เอาร้านนี้ตลอดไป
  (•) แค่วันนี้ — หายเมื่อเที่ยงคืน

  [ยกเลิก] [ยืนยัน]
  ```
- [ ] Submit → `POST /blacklist` → refresh list

### List Display

- [ ] Call `GET /blacklist` on page load
- [ ] React Query for caching + auto-refetch
- [ ] Group by mode: "ถาวร" section + "วันนี้" section
- [ ] ถ้าว่าง → empty state: "ยังไม่มี blacklist 🎉"

### Delete Action

- [ ] ปุ่ม [ลบ] ข้างแต่ละรายการ
- [ ] Click → confirmation dialog: "ลบ 'ส้มตำนัว' ออกจาก blacklist?"
- [ ] Confirm → `DELETE /blacklist/{id}` → remove from list
- [ ] Toast notification: "ลบสำเร็จ ✅"

### Bulk Operations (Optional)

- [ ] Checkbox ข้างแต่ละร้าน
- [ ] ปุ่ม "ลบที่เลือก" → batch delete
- [ ] POC: skip — single delete ก็พอ

### Mode Change (Optional)

- [ ] ปุ่ม "เปลี่ยนเป็นถาวร" ข้างรายการ today-mode
- [ ] กด → update mode → reload

### Empty State & Error Handling

- [ ] Empty state: icon + text + CTA
- [ ] Loading state: skeleton
- [ ] Error state: retry button
- [ ] Toast for all actions (add/remove)

---

## 📋 Acceptance Criteria

✅ Search ร้าน → result แสดงภายใน 1 วินาที
✅ เพิ่ม blacklist → list update ทันที
✅ ลบ blacklist → list update ทันที
✅ Today-mode entry แสดง badge "วันนี้"
✅ Permanent entry แสดง badge "ถาวร"
✅ Mobile responsive — ใช้บนมือถือได้สบาย
✅ Keyboard navigation (tab, enter) ทำงาน

---

## 📝 Technical Notes

### React Query Setup
```typescript
const { data: blacklist } = useQuery({
  queryKey: ['blacklist'],
  queryFn: () => api.get('/blacklist').then(r => r.json())
});

const addMutation = useMutation({
  mutationFn: (payload) => api.post('/blacklist', payload),
  onSuccess: () => queryClient.invalidateQueries(['blacklist'])
});
```

### Search with Debounce
```typescript
import { useDebouncedValue } from '@/lib/hooks';
const [query, setQuery] = useState('');
const debouncedQuery = useDebouncedValue(query, 300);

const { data: results } = useQuery({
  queryKey: ['search', debouncedQuery],
  queryFn: () => api.get(`/restaurants?search=${debouncedQuery}`).then(r => r.json()),
  enabled: debouncedQuery.length >= 2
});
```

### Accessibility
- All buttons: `aria-label`
- Modal: focus trap
- Color contrast ≥ AA

### UI Framework
- shadcn/ui primitives
- Tailwind for custom styles
- Lucide icons

## 🔗 Reference

- `design.md` → Phase 4 Web App
- Task 006 — Blacklist API
