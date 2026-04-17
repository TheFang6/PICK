# 018 — Deploy Frontend to Vercel

**Phase:** 5 (Deploy)
**Estimated Time:** 2-3 ชม.
**Dependencies:** 014, 017

---

## 🎯 Goal

Deploy Next.js web app บน Vercel — connect กับ backend + public URL สำหรับ pairing flow

---

## ✅ Subtasks

### Vercel Project Setup

- [ ] สมัคร Vercel account (https://vercel.com)
- [ ] New Project → Import Git Repository
- [ ] เลือก repo + root directory = `web/`
- [ ] Framework Preset: Next.js (auto-detect)
- [ ] Build Settings:
  - Build Command: `npm run build`
  - Output Directory: `.next`
  - Install Command: `npm install`

### Environment Variables

- [ ] Vercel → Project → Settings → Environment Variables:
  ```
  NEXT_PUBLIC_API_URL=https://pick-backend.up.railway.app
  ```
- [ ] Set scope: Production + Preview + Development
- [ ] Preview URL สำหรับ PR testing

### Domain Configuration

- [ ] Generate Vercel domain: `pick.vercel.app`
- [ ] (Optional) Custom domain:
  - `pick.app` หรือ `app.pick.com`
  - Add CNAME record → `cname.vercel-dns.com`
  - HTTPS auto (Let's Encrypt)

### CORS Update (Backend)

- [ ] Railway backend → `ALLOWED_ORIGINS` env var:
  ```
  https://pick.vercel.app,https://pick.app,http://localhost:3000
  ```
- [ ] Redeploy backend

### Cookie Domain (Production)

- [ ] Backend set cookie:
  ```python
  response.set_cookie(
      "session_id",
      token,
      httponly=True,
      samesite="lax",
      secure=True,  # production MUST be True
      domain=".pick.app",  # ถ้าใช้ subdomain
  )
  ```
- [ ] Cross-origin: `secure=True` + `samesite=None`? (test)

### Deployment Flow

- [ ] Git push `main` → Vercel auto-deploy
- [ ] PR → preview deployment URL
- [ ] Production URL = stable domain
- [ ] Rollback: Vercel dashboard → Deployments → Promote to Production

### Build Optimization

- [ ] `next.config.mjs`:
  ```js
  export default {
    reactStrictMode: true,
    images: { remotePatterns: [{ hostname: 'maps.googleapis.com' }] },
    experimental: { optimizePackageImports: ['lucide-react'] }
  }
  ```
- [ ] Enable Image Optimization (ดึงรูปร้านจาก Google)

### Analytics (Optional)

- [ ] Vercel Analytics → enable (ฟรี 2500 events/mo)
- [ ] หรือ Plausible / PostHog

### Performance Checks

- [ ] Lighthouse score > 90 (Performance, A11y)
- [ ] Core Web Vitals: LCP < 2.5s, CLS < 0.1
- [ ] Bundle analyzer: `@next/bundle-analyzer`

### Error Monitoring (Optional)

- [ ] Sentry for Next.js
  ```bash
  npx @sentry/wizard@latest -i nextjs
  ```
- [ ] POC: skip — ใช้ Vercel error dashboard

### Telegram Deep Link Update

- [ ] Bot `/start` message:
  ```
  เปิดหน้าเว็บ: https://pick.vercel.app/pair?token={UUID}
  ```
- [ ] Env var ใน backend: `WEB_URL=https://pick.vercel.app`

---

## 📋 Acceptance Criteria

✅ `pick.vercel.app` เปิดได้ → แสดงหน้า landing
✅ `/pair?token=X` → pairing สำเร็จ → redirect ไป `/blacklist`
✅ Cookie session ทำงาน — refresh browser ยัง login อยู่
✅ Mobile browser (Chrome iOS/Android) — responsive ดี
✅ HTTPS ทำงาน — padlock ใน browser
✅ API calls cross-origin ทำงาน (CORS ผ่าน)
✅ Preview deployment สำหรับ PR ทำงาน

---

## 📝 Technical Notes

### Vercel Pricing (POC)
- Hobby plan: Free
- 100GB bandwidth/mo
- Unlimited deploys

### SameSite Cookie Issues
- Cross-origin: `samesite="none"` + `secure=True` required
- Same-origin (subdomain): `samesite="lax"` ใช้ได้
- Fix: ใช้ subdomain `api.pick.app` + `pick.app` → same parent domain

### Caching Strategy
```js
// app/page.tsx
export const revalidate = 60; // ISR 60s
```
- Static pages: CDN edge cache
- Dynamic (auth): `cache: 'no-store'`

### Next.js Middleware (Optional)
```ts
// middleware.ts
export function middleware(request) {
  const session = request.cookies.get('session_id');
  if (!session && request.nextUrl.pathname.startsWith('/blacklist')) {
    return NextResponse.redirect(new URL('/', request.url));
  }
}
```

### Build Output Size
- Target: < 1MB initial JS bundle
- ลด: dynamic import สำหรับ heavy components

### Preview Deployment Workflow
1. PR opened → Vercel creates preview URL
2. Comment on PR with URL + Lighthouse score
3. Test manually → merge → auto-deploy production

## 🔗 Reference

- `design.md` → Phase 5 Deploy
- Vercel docs: https://vercel.com/docs
- Task 014 — Web project setup
