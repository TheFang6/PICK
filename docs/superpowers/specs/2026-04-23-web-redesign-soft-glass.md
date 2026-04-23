# PICK Web App Redesign — Soft Glass (Design 3)

**Date:** 2026-04-23  
**Status:** Approved  
**Scope:** Full web app visual redesign — no backend changes, no new features

---

## Summary

Replace the current grayscale shadcn design with a "Soft Glass" aesthetic: indigo/violet accent color, frosted glass cards, subtle gradient background, and pill-shaped interactive elements. Desktop-first, responsive on mobile.

---

## Design System Changes

### Color Tokens (globals.css)

Replace all current CSS variables with:

```css
:root {
  /* Background: soft indigo-to-violet gradient */
  --background: oklch(0.97 0.01 280);
  --foreground: oklch(0.13 0 0);

  /* Glass cards */
  --card: oklch(1 0 0 / 65%);
  --card-foreground: oklch(0.13 0 0);

  /* Primary: indigo */
  --primary: oklch(0.525 0.22 264);          /* #4f46e5 */
  --primary-foreground: oklch(1 0 0);

  /* Secondary: violet */
  --secondary: oklch(0.97 0.03 280);
  --secondary-foreground: oklch(0.525 0.22 264);

  /* Muted */
  --muted: oklch(0.96 0.01 280);
  --muted-foreground: oklch(0.55 0 0);

  /* Accent: light indigo tint */
  --accent: oklch(0.94 0.04 264);
  --accent-foreground: oklch(0.525 0.22 264);

  /* Destructive: red */
  --destructive: oklch(0.577 0.245 27.325);

  /* Borders: semi-transparent white */
  --border: oklch(1 0 0 / 75%);
  --input: oklch(1 0 0 / 65%);
  --ring: oklch(0.525 0.22 264);

  /* Radius: increased for softer look */
  --radius: 0.875rem;
}
```

Body background uses a CSS gradient (not a single token):
```css
body {
  background: linear-gradient(135deg, #eef2ff 0%, #f5f3ff 40%, #faf5ff 100%);
  min-height: 100vh;
}
```

### Typography

Keep Geist Sans. No changes to font imports.

### Border Radius

Increase `--radius` from `0.625rem` to `0.875rem`. All computed variants (`--radius-sm` through `--radius-4xl`) scale automatically.

---

## Component Changes

### Nav (`components/pick/Nav.tsx`)

- Background: `rgba(255,255,255,0.7)` with `backdrop-filter: blur(16px)`
- Border-bottom: `rgba(255,255,255,0.8)`
- Logo: gradient text (indigo → violet) via `bg-clip-text`
- Nav links: pill-shaped (`rounded-full`), active state uses `bg-primary text-primary-foreground`
- Avatar: gradient circle with box-shadow
- Logout: ghost button, `rounded-full`, semi-transparent background

### Button (`components/ui/button.tsx`)

Update CVA variants:
- `default`: gradient background `from-indigo-600 to-violet-600`, `rounded-full`, box shadow on hover
- `outline`: semi-transparent white bg, white border, `rounded-full`
- `destructive`: keep red but `rounded-full`
- `ghost`: `rounded-full`

### Card (`components/ui/card.tsx`)

Add glassmorphism styling:
- Background: `rgba(255,255,255,0.65)`
- `backdrop-filter: blur(20px)`
- Border: `rgba(255,255,255,0.85)`
- Border-radius: `--radius-2xl` (≈20px)
- Box-shadow: subtle indigo-tinted shadow

### Input (`components/ui/input.tsx`)

- Background: `rgba(255,255,255,0.7)`
- Border: `rgba(255,255,255,0.8)`
- `rounded-full` (pill shape)
- Focus ring: indigo with alpha

### Checkbox

- Unchecked: `rgba(255,255,255,0.8)` bg, light border
- Checked: indigo gradient bg

---

## Page Changes

### Login / Home (`app/page.tsx`)

- Center the login card on the gradient background
- Card uses glassmorphism
- "Connect with Telegram" button uses `default` gradient variant

### Pair (`app/pair/page.tsx`)

- Same glassmorphism card treatment
- No functional changes

### Blacklist (`app/blacklist/page.tsx`)

- Page title: "Restaurant **Blacklist**" with gradient span on second word
- Subtitle: muted text
- Search input: pill-shaped with glass background
- Filter tabs: pill buttons (`rounded-full`), active = indigo solid
- "Add restaurant" button: gradient primary
- "Remove selected" button: ghost destructive (`rounded-full`)
- List card: glassmorphism
- List items: emoji icon in indigo-tinted rounded square, hover lift
- Badges: `badge-permanent` = light red pill, `badge-daily` = light amber pill

### History (`app/history/page.tsx`)

- Mine/Team tabs: pill toggle group, glass bg
- Month nav: circular ghost buttons
- Calendar card: glassmorphism
- Calendar day cells:
  - Has lunch: white glass cell, emoji food icon above date number, hover lift + shadow
  - Today: indigo border + light indigo bg
  - Selected: indigo gradient tint + shadow
  - Weekend: muted number color
  - Empty (other month): very muted
- **New:** click a day → detail panel below calendar
  - Vote breakdown cards (2-column grid)
  - Winner card: indigo-tinted border
  - Vote bar: indigo gradient fill
  - Attendee avatar stack (colored initials, white border, overlap)
  - 👑 icon on winner

---

## What Does NOT Change

- All API calls, data fetching, React Query setup
- Authentication flow and session handling
- Functional behavior of all pages
- TypeScript types
- Backend integration

---

## Implementation Notes

- Glass cards require `backdrop-filter` — ensure `isolation: isolate` on parent where needed
- Gradient text uses `bg-clip-text text-transparent bg-gradient-to-r`
- Tailwind 4 supports arbitrary values; use `bg-white/65`, `border-white/75` for glass effects
- The detail panel on history page is new UI (click handler + conditional render)
- No dark mode changes required for this scope — keep existing dark mode tokens

---

## Files to Change

| File | Change |
|------|--------|
| `app/globals.css` | New color tokens + body gradient |
| `app/layout.tsx` | Possibly remove bg-background from body if set |
| `components/pick/Nav.tsx` | Glass nav, gradient logo, pill links |
| `components/ui/button.tsx` | Gradient primary, pill variants |
| `components/ui/card.tsx` | Glassmorphism styles |
| `components/ui/input.tsx` | Glass + pill input |
| `app/page.tsx` | Glass login card |
| `app/pair/page.tsx` | Glass card treatment |
| `app/blacklist/page.tsx` | Full redesign per spec |
| `app/history/page.tsx` | Calendar redesign + detail panel |
