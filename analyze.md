# PICK — Code Analysis (Updated)

> อัปเดตครั้งที่ 2 จาก source code ทั้งหมด วันที่ 2026-04-23 (หลัง session)

---

## 1. Overview

**PICK** คือ Lunch Bot สำหรับทีม office ใช้ Telegram เป็น interface หลัก มี Web App เสริม

```
Users (Telegram)
    │
    ▼
Telegram Bot  ──────────▶  FastAPI Backend  ◀──────  Web App (Next.js)
                               │
                    ┌──────────┼──────────┐
                    ▼          ▼          ▼
               PostgreSQL  Google Maps  In-Memory
               (Railway)      API      Session Pool
```

### Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Backend | FastAPI + SQLAlchemy + Pydantic v2 | FastAPI ≥0.111, SQLAlchemy ≥2.0 |
| Database | PostgreSQL (via Railway) | — |
| ORM Migration | Alembic | ≥1.13 |
| Bot | python-telegram-bot | v20+ |
| Frontend | Next.js + TypeScript + shadcn/ui + Tailwind | Next.js 16.2.4, React 19.2.4 |
| External API | Google Maps Places API (Nearby Search) | — |
| HTTP Client | httpx | ≥0.27 |
| State (Frontend) | React Query (@tanstack/react-query) | v5.99.2 |

### Project Status (as of 2026-04-23)

| Phase | Tasks | Status |
|-------|-------|--------|
| Phase 1: Foundation | 4 tasks | ✅ Done |
| Phase 2: Core Logic | 5 tasks | ✅ Done |
| Phase 3: Telegram Bot | 6 tasks | ✅ Done |
| Phase 4: Web App | 3 tasks | ✅ Done |
| Phase 5: Deploy | 2 tasks | ❌ Remaining |
| **Total** | **19 tasks** | **16/19 Done (84%)** |

---

## 2. Project Structure

```
pick/
├── backend/
│   ├── app/
│   │   ├── main.py              ← FastAPI app + CORS + 9 routers
│   │   ├── config.py            ← Settings (pydantic-settings, .env)
│   │   ├── database.py          ← SQLAlchemy engine + get_db
│   │   ├── api/                 ← REST endpoints (9 routers)
│   │   │   ├── restaurants.py   ← CRUD + sync Google Maps
│   │   │   ├── recommend.py     ← /recommend (core algorithm)
│   │   │   ├── history.py       ← User & team history
│   │   │   ├── blacklist.py     ← Add/remove/list blacklist
│   │   │   ├── attendance.py    ← /attendance/today
│   │   │   ├── gacha.py         ← /gacha/{session_id} roll
│   │   │   ├── pair.py          ← Web auth (pair/me/logout)
│   │   │   ├── telegram.py      ← Webhook endpoint
│   │   │   └── dev.py           ← /dev/nearby (debug)
│   │   ├── bot/
│   │   │   ├── application.py   ← Bot setup + handler registration
│   │   │   ├── handlers/        ← 9 handler files
│   │   │   └── poll_timeout.py  ← Auto-complete expired polls
│   │   ├── models/              ← SQLAlchemy ORM (8 tables)
│   │   ├── schemas/             ← Pydantic request/response models
│   │   ├── services/            ← Business logic (12 files)
│   │   └── tests/unit/          ← 17 unit test files (pytest)
│   ├── alembic/                 ← DB migrations (7 migrations)
│   └── railway.toml             ← Railway deploy config
├── web/
│   ├── app/
│   │   ├── page.tsx             ← Landing page
│   │   ├── pair/page.tsx        ← Telegram pairing flow
│   │   ├── blacklist/page.tsx   ← Blacklist management
│   │   ├── history/page.tsx     ← Calendar history view
│   │   ├── layout.tsx           ← Root layout + providers
│   │   └── api/[...path]/       ← Proxy → FastAPI backend
│   ├── components/pick/         ← Nav, Providers
│   ├── lib/                     ← api.ts, auth.ts, hooks.ts, utils.ts
│   └── railway.toml             ← Railway deploy config
├── tasks/                       ← Task planning files (INDEX.md + 19 tasks)
├── design.md                    ← Main design document
├── analyze.md                   ← This file
└── next-feature.md              ← Future feature backlog
```

---

## 3. Database Schema (9 Tables, 7 Migrations)

### Migrations Order
1. **995ad0e072c8** — users + restaurants
2. **1991e2f3d3bc** — lunch_history
3. **855e8189a896** — user_blacklist
4. **7b1ab9603757** — pairing_tokens
5. **ef50f8b44f33** — user_attendance
6. **a367868b9af9** — poll_sessions + poll_votes
7. **b1c2d3e4f5a6** — web_sessions
8. **c7d8e9f0a1b2** — add user_ratings_total to restaurants

### Entity Relationship Diagram

```
users ──────────────────────────────────────────────────┐
  │ id (PK)                                              │
  │ telegram_id (UNIQUE)                                 │
  │ name                                                 │
  │ created_at                                           │
  │                                                      │
  ├──── user_blacklist ────┐                             │
  │      user_id (FK)      │                             │
  │      restaurant_id (FK)├──── restaurants             │
  │      mode (permanent/today)  id (PK)                 │
  │      expires_at         place_id (UNIQUE, nullable)  │
  │                         name                         │
  ├──── user_attendance     source (google_maps/manual)  │
  │      user_id (FK)       lat, lng                     │
  │      date               vicinity                     │
  │      status (IN/WFH/UNKNOWN) rating                  │
  │                         price_level                  │
  ├──── pairing_tokens      types (JSON)                 │
  │      user_id (FK)       photo_reference              │
  │      token (UNIQUE)     closed_weekdays (JSON)       │
  │      expires_at         closed_monthly_ranges (JSON) │
  │                         added_by (FK→users)          │
  ├──── web_sessions        last_fetched_at              │
  │      user_id (FK)       created_at                   │
  │      session_token (UNIQUE)    │                     │
  │      expires_at         │      │                     │
  │                         ▼      ▼                     │
  └──── poll_sessions ─── lunch_history                  │
         created_by (FK)   restaurant_id (FK)            │
         candidates (JSON) date                          │
         winner_restaurant_id (FK) attendees (JSON)      │
         status            created_at                    │
         expires_at                                      │
         │                                               │
         └──── poll_votes                                │
                poll_session_id (FK)                     │
                user_id (FK) ───────────────────────────┘
                restaurant_id (FK)
                UNIQUE(poll_session_id, user_id)
```

---

## 4. API Endpoints (15+ Routes, 9 Routers)

### Restaurants Router
| Method | Path | Description |
|--------|------|-------------|
| GET | `/restaurants` | List with pagination + search |
| GET | `/restaurants/{id}` | Get single restaurant |
| POST | `/restaurants/manual` | Create manual restaurant |
| PUT | `/restaurants/{id}` | Update (owner only) |
| DELETE | `/restaurants/{id}` | Delete (owner only) |
| POST | `/restaurants/sync-from-maps` | Sync from Google Maps |

### Core Routers
| Method | Path | Description |
|--------|------|-------------|
| POST | `/recommend` | Run recommendation algorithm |
| POST | `/gacha/{session_id}` | Roll gacha (max 5) |
| GET | `/history` | User personal history |
| GET | `/history/team` | Team history |
| POST | `/history` | Log a lunch |
| POST | `/blacklist` | Add to blacklist |
| DELETE | `/blacklist/{id}` | Remove from blacklist |
| GET | `/blacklist` | List user's blacklist |
| GET | `/attendance/today` | Today's attendees |
| POST | `/pair` | Pair Telegram ↔ Web |
| GET | `/me` | Get current user (web auth) |
| POST | `/logout` | Invalidate web session |
| POST | `/webhook/telegram` | Telegram webhook receiver |
| GET | `/dev/nearby` | Debug Google Maps response |

---

## 5. Telegram Bot Commands & Callbacks

### Command Handlers (9 commands)

| Command | Context | What it does |
|---------|---------|--------------|
| `/start` | DM | Register user + generate pairing token + send web link |
| `/help` | Any | Show command list (MarkdownV2 formatted) |
| `/lunch` | Group | Create poll with 3 candidates + voting buttons |
| `/lunch` | DM | Send 3 picks with click-to-confirm |
| `/gacha` | Any | Solo random pick + reroll button |
| `/in` | Any | Set attendance → IN_OFFICE |
| `/wfh` | Any | Set attendance → WFH |
| `/blacklist add/list/remove` | Any | Manage personal blacklist |
| `/addrestaurant` | Any | Conversation: name→price→category→closed days→confirm |
| `/editrestaurant` | Any | Select manual restaurant → edit submenu |

### Callback Handlers (10 callback patterns)

| Callback Pattern | Action |
|-----------------|--------|
| `vote:<poll_id>:<index>` | Cast vote, update live vote counts |
| `cancel:<poll_id>` | Creator cancels poll |
| `gacha:<poll_id>` | Random pick → auto-log → complete poll |
| `skip:<poll_id>:<index>` | Replace one candidate from pool |
| `dm_pick:<restaurant_id>` | Confirm DM pick → log lunch |
| `gacha_ok:<restaurant_id>` | Confirm solo gacha → log lunch |
| `gacha_reroll` | Get new solo random pick |
| `bl_pick:<restaurant_id>` | Select restaurant to blacklist |
| `bl_mode:<restaurant_id>:<mode>` | Choose permanent or today blacklist |
| `bl_rm:<blacklist_id>` | Remove from blacklist |

---

## 6. Recommendation Algorithm (Core Logic)

**File:** `backend/app/services/recommendation.py`

### Pipeline Flow (5 Stages)

```
Stage 1: FETCH
   Google Maps API search_nearby()
   → upsert DB (places table)
   → track closed_place_ids

Stage 2: FILTER (removes restaurants that fail ANY rule)
   ├── Recently visited (7 days from lunch_history)
   ├── Blacklisted by any attendee (permanent or today)
   ├── Permanently closed (Google status)
   ├── Closed today (open_now=False from Google)
   ├── Closed this weekday (closed_weekdays JSON field)
   ├── In closed monthly range (closed_monthly_ranges)
   └── Outside radius (haversine distance > office_radius)

Stage 3: PRE-FILTER by quality
   Filter out: rating < RATING_THRESHOLD (default 3.8)
   Filter out: user_ratings_total < RATINGS_COUNT_THRESHOLD (default 20)
   ← Both thresholds configurable via env vars

Stage 4: BUILD POOL (uniform weight)
   Shuffle remaining restaurants randomly
   → take first 10 (uniform weight 1.0 each)
   ← NOT score-ranked, pure random shuffle

Stage 5: SAMPLE
   Weighted random from pool (all weights = 1.0 → effectively uniform)
   → pick 3 distinct candidates
   → create in-memory gacha session
   → return {candidates, pool, session_id, remaining_rolls: 5}
```

### Haversine Distance
```python
def _haversine(lat1, lng1, lat2, lng2) -> float:
    # Returns distance in meters
    # Used in both filter (radius check) and score (distance_score)
```

---

## 7. Gacha System

**Files:** `backend/app/services/gacha.py`, `backend/app/services/session_pool.py`

### In-Memory Session Structure
```python
_sessions: dict[str, dict] = {
    "session_uuid": {
        "pool": [(Restaurant, score), ...],  # Top 10 from recommendation
        "gacha_count": 0,                    # 0-5 rolls done
        "previous_picks": {restaurant_id},   # Already shown UUIDs
        "expires_at": datetime,              # 2 hours from creation
    }
}
```

### Roll Flow
```
roll(session_id, k=3)
  ├── Check session exists → raise SessionNotFound
  ├── Check expiry → raise SessionExpired
  ├── Filter pool: exclude previous_picks
  ├── If all picked → reset pool to full
  ├── Sample 3 weighted random from remaining
  ├── Increment gacha_count
  ├── Add new picks to previous_picks
  └── If gacha_count >= 5 → raise GachaLimitExceeded
```

### Exceptions
- `SessionNotFound` → HTTP 404
- `SessionExpired` → HTTP 410
- `GachaLimitExceeded` → HTTP 429

---

## 8. Blacklist System

### Two Modes

| Mode | Expiry | Use Case |
|------|--------|----------|
| `permanent` | Never (manual remove) | Don't like this restaurant |
| `today` | 23:59:59 same day | Already went, skip today only |

### Filtering Logic
```python
blacklisted_ids = blacklist_repo.get_blacklisted_restaurant_ids(db, user_ids)
# Query excludes expired entries (expires_at < now OR expires_at IS NULL)
# Any attendee's blacklist blocks the restaurant for whole group
```

---

## 9. Web App (Frontend)

### Authentication Flow
```
1. /start in Telegram
   → bot creates PairingToken (10-min TTL)
   → sends web link: {WEB_URL}/pair?token=<token>

2. User opens /pair?token=<token>
   → POST /pair with token
   → backend validates token, creates WebSession (30-day TTL)
   → sets HttpOnly cookie: session_id
   → redirect → /blacklist

3. All subsequent requests: cookie auto-sent
   → 401? redirect → /pair (re-auth)
```

### Pages

| Page | Route | Features |
|------|-------|----------|
| Landing | `/` | Intro + Telegram link + expired session message |
| Pairing | `/pair` | Token extraction → POST /pair → redirect |
| Blacklist | `/blacklist` | Search restaurants, bulk select, add permanent/today, view & remove |
| History | `/history` | Calendar view, Mine/Team tabs, month navigation, day detail |

### API Proxy
```
/api/[...path]/route.ts
  → proxy all HTTP methods to backend
  → preserve cookies (credentials: include)
  → forward all headers
```

### UI Components
- **shadcn/ui:** button, card, dialog, input, sonner (toasts)
- **Custom:** Nav (navigation bar), Providers (React Query + theme)
- **Tailwind CSS:** glass morphism styling

---

## 10. Configuration & Environment

**Backend** (`backend/app/config.py`):

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | ✅ | — | PostgreSQL connection string |
| `GOOGLE_MAPS_API_KEY` | ✅ | `""` | Google Maps API key |
| `TELEGRAM_BOT_TOKEN` | ✅ | `""` | Telegram Bot API token |
| `TELEGRAM_WEBHOOK_SECRET` | ❌ | `""` | Webhook secret header |
| `BASE_URL` | ❌ | `""` | Backend base URL |
| `WEB_URL` | ❌ | `https://pick.vercel.app` | Frontend URL |
| `ALLOWED_ORIGINS` | ❌ | `http://localhost:3000` | CORS origins |
| `DEBUG` | ❌ | `false` | Debug mode |
| `OFFICE_LAT` | ❌ | `18.7964464` | Office latitude |
| `OFFICE_LNG` | ❌ | `99.0164042` | Office longitude |
| `OFFICE_RADIUS` | ❌ | `1000` | Search radius (meters) |
| `RATING_THRESHOLD` | ❌ | `3.8` | Min rating to be recommended |
| `RATINGS_COUNT_THRESHOLD` | ❌ | `20` | Min review count to be recommended |

**Frontend** (`web/.env.local`):

| Variable | Description |
|----------|-------------|
| `NEXT_PUBLIC_API_URL` | Backend base URL |

---

## 11. Testing

**17 unit test files** (pytest + SQLite in-memory)

| File | Tests |
|------|-------|
| `test_recommendation.py` | Algorithm: haversine, filtering, scoring, sampling |
| `test_gacha.py` | Session pool, roll mechanics, limits |
| `test_lunch_poll.py` | Poll CRUD, voting, winner logic |
| `test_restaurants.py` | CRUD: manual + Google Maps |
| `test_history.py` | Logging, history queries |
| `test_blacklist.py` | Add/remove/list, modes, expiry |
| `test_attendance.py` | Status setting, attendee queries |
| `test_gacha_bot.py` | Solo gacha command & reroll |
| `test_blacklist_bot.py` | Blacklist commands |
| `test_restaurant_cmd.py` | Add/edit conversation flows |
| `test_pair.py` | Pairing token lifecycle |
| `test_google_maps.py` | API integration (mocked) |
| `test_telegram_bot.py` | Handler registration & basic flows |
| `test_web_features.py` | Auth, web endpoints |
| `test_health.py` | Health check endpoint |

### Test Patterns
- SQLite in-memory for DB tests
- Mock Google Maps API responses
- Fake Restaurant dataclasses

---

## 12. Scoring Weights & Design Decisions

### Recommendation Algorithm (Current Implementation)
```
1. Filter: rating >= RATING_THRESHOLD (default 3.8)
2. Filter: user_ratings_total >= RATINGS_COUNT_THRESHOLD (default 20)
3. build_pool: shuffle randomly → take first 10 (uniform weight)
4. sample_candidates: weighted random pick 3 (all weights=1.0 → uniform)
```

> ⚠️ NOTE: ไม่ใช้ score-based ranking แล้ว — เปลี่ยนเป็น random shuffle หลัง quality filter
> Scoring formula (rating×0.50 + log1p(reviews)×0.35 + ...) ถูก remove ออกแล้ว

### Key Design Decisions
1. **In-Memory Gacha Pool** — Fast reads, no DB round-trips per roll (trade-off: lost on restart)
2. **Uniform Random Sampling** — `build_pool` shuffles randomly then takes 10 (weight=1.0 each), not score-ranked
3. **Quality Pre-filter** — Min rating 3.8 + min 20 reviews required, both configurable via `RATING_THRESHOLD` / `RATINGS_COUNT_THRESHOLD` env vars
4. **Blacklist Any-User-Blocks** — If anyone blacklists a place, whole group skips it
5. **Attendance Auto-Include** — UNKNOWN status = IN_OFFICE (opt-out model, not opt-in)
6. **Google Maps Upsert** — `INSERT...ON CONFLICT UPDATE` prevents duplicates, saves `user_ratings_total`
7. **Today-Only Blacklist** — Uses `expires_at` (auto-filtered), no separate cron needed
8. **5-Roll Gacha Limit** — Balanced between variety and decision fatigue
9. **Known Bug** — Restaurants in DB but absent from current Google Maps results bypass `open_now` filter → evening-only restaurants like "opens 17:00" can appear at lunchtime

---

## 13. What's Implemented vs Planned

### Implemented (16/19)
- ✅ FastAPI backend + PostgreSQL schema (7 migrations, 8 tables)
- ✅ Google Maps Nearby Search integration + upsert caching
- ✅ Restaurant CRUD (manual + Google Maps source)
- ✅ Recommendation pipeline (5 stages: fetch→filter→score→pool→sample)
- ✅ Lunch history tracking (user + team)
- ✅ Blacklist system (permanent + today modes)
- ✅ In-memory gacha with 5-roll limit + weighted sampling
- ✅ Telegram bot: 9 commands + 10 callback patterns
- ✅ Attendance tracking (/in, /wfh)
- ✅ Group lunch polling with live vote counts
- ✅ Gacha within polls (replace candidate)
- ✅ Manual restaurant CRUD via bot conversation
- ✅ Web app: pairing, blacklist management, history calendar
- ✅ Web auth: HttpOnly session cookie + 30-day TTL

### Remaining (3/19)
- ❌ **Deploy backend to Railway** — Task 018
- ❌ **Deploy frontend to Railway** — Task 019
- ❌ **E2E testing (Playwright)** — Playwright config exists, no tests written yet

### Future (next-feature.md, Post-POC)
- Google Maps cache strategies (daily/weekly refresh)
- Dynamic radius based on pool size
- Multi-cuisine type search
- Favorites system (❤️)
- Frequent detection (auto-penalize repeat restaurants)
- Restaurant closed/out-of-stock fallback (Tier 3)
- Adaptive gacha limits by team size

---

## 14. Statistics

| Metric | Count |
|--------|-------|
| Database tables | 8 |
| Alembic migrations | 8 |
| API endpoints | 15+ |
| Bot commands | 9 |
| Bot callback patterns | 10 |
| Frontend pages | 4 + proxy |
| Service/repo files | 12 |
| Unit test files | 19 |
| Tasks completed | 16/19 (84%) |
| Estimated dev time | ~10 days |
