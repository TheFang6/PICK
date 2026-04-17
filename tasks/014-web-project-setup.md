# 014 — Web Project Setup

**Phase:** 4 (Web App)
**Estimated Time:** 4-6 ชม.
**Dependencies:** 008

---

## 🎯 Goal

Setup Next.js project + pairing flow — web session ผูกกับ Telegram account ผ่าน token

---

## ✅ Subtasks

### Project Initialization

- [ ] `npx create-next-app@latest web --ts --tailwind --app`
- [ ] Install dependencies:
  - [ ] `@tanstack/react-query`
  - [ ] `react-hook-form`
  - [ ] `zod` (validation)
  - [ ] `lucide-react` (icons)
  - [ ] `clsx` (class utils)
- [ ] Install shadcn/ui:
  - [ ] `npx shadcn@latest init`
  - [ ] Add components: button, input, card, dialog, toast
- [ ] Folder structure:
  ```
  web/
  ├── app/
  │   ├── layout.tsx
  │   ├── page.tsx
  │   ├── pair/
  │   │   └── page.tsx
  │   ├── blacklist/
  │   │   └── page.tsx
  │   └── history/
  │       └── page.tsx
  ├── components/
  │   ├── ui/        # shadcn components
  │   └── pick/      # custom components
  ├── lib/
  │   ├── api.ts     # API client
  │   ├── auth.ts    # session helpers
  │   └── utils.ts
  ├── .env.local
  └── next.config.mjs
  ```

### Environment Variables

- [ ] `.env.local`:
  ```
  NEXT_PUBLIC_API_URL=http://localhost:8000
  ```
- [ ] `.env.example` เดียวกันแต่ placeholders

### Pairing Flow — Frontend

- [ ] Page: `/pair` (app/pair/page.tsx)
- [ ] Logic:
  1. Read `token` จาก URL query
  2. Call `POST /api/pair { token }`
  3. ถ้าสำเร็จ:
     - Backend set HTTP-only cookie
     - Redirect → `/blacklist` หรือ `/history`
  4. ถ้า error:
     - แสดง error message + ปุ่ม "กลับไป Telegram"

### Pairing Flow — Backend

- [ ] Endpoint: `POST /pair` (ใน task 008 หรือ extend)
- [ ] Logic:
  1. Receive `token` จาก body
  2. Query `pairing_tokens` → verify ไม่หมดอายุ + ยังไม่ใช้
  3. Mark `consumed_at = now()`
  4. Create session → set HTTP-only cookie (`Set-Cookie: session_id=xxx; HttpOnly; SameSite=Lax`)
  5. Return `{ user_id, name }`

### Session Management

- [ ] สร้าง `app/models/web_session.py`:
  ```python
  web_sessions:
    id (UUID, PK)
    user_id (UUID, FK users)
    session_token (TEXT, UNIQUE)  # stored in cookie
    expires_at (TIMESTAMP)
    created_at (TIMESTAMP)
  ```
- [ ] Middleware: `require_session` — check cookie → load user
- [ ] Session lifetime: 30 วัน

### API Client Wrapper

- [ ] `lib/api.ts`:
  ```typescript
  export const api = {
    get: (path: string) => fetch(`${API_URL}${path}`, { credentials: 'include' }),
    post: (path, body) => fetch(...),
    delete: (path) => fetch(...)
  }
  ```
- [ ] Handle 401 → redirect ไป `/` + แสดง "please pair again"

### Layout & Navigation

- [ ] Root layout: basic header with user name + logout
- [ ] Navigation: Blacklist | History | Logout
- [ ] Mobile-first design (large buttons, padding)

### Landing Page

- [ ] `/` page: "PICK — Lunch Bot. Pair ก่อนใช้งานจาก Telegram bot /start"
- [ ] ลิงก์ไป bot: `https://t.me/PickLunchBot`

---

## 📋 Acceptance Criteria

✅ `npm run dev` รันที่ `localhost:3000`
✅ Pairing flow: `/start` → click link → `/pair?token=X` → redirect สำเร็จ
✅ Cookie HttpOnly + SameSite=Lax
✅ Session expires 30 วัน
✅ `/blacklist` และ `/history` access ไม่ได้ถ้าไม่มี session → redirect กลับ
✅ Token ใช้แล้ว ใช้ซ้ำไม่ได้

---

## 📝 Technical Notes

### CORS Config (Backend)
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://pick.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Cookie Settings
```python
response.set_cookie(
    key="session_id",
    value=token,
    httponly=True,
    samesite="lax",
    secure=True,  # production only
    max_age=30*24*3600,
)
```

### App Router vs Pages Router
- ใช้ App Router (Next.js 14+) — modern, server components
- `/pair` = client component (ต้อง read URL params)
- `/blacklist`, `/history` = mix (server fetch + client state)

### State Management
- React Query สำหรับ API calls
- No global state library (Zustand, Redux) — POC ไม่ต้อง

## 🔗 Reference

- `design.md` → Phase 4 Web App
- Task 008 — Pairing token generation
