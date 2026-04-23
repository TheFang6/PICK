# PICK Backend — Project Structure

```
backend/
├── app/                          # Application source code
│   ├── main.py                   # FastAPI app entry point, registers all routers
│   ├── config.py                 # Environment config (DATABASE_URL, API keys, bot token)
│   ├── database.py               # SQLAlchemy engine, session factory, get_db dependency
│   │
│   ├── api/                      # API layer — receives HTTP requests, returns responses
│   │   ├── attendance.py         # GET /attendance/today — today's office attendees
│   │   ├── blacklist.py          # POST /blacklist, DELETE /blacklist/{id}, GET /blacklist
│   │   ├── dev.py                # Developer/debug endpoints
│   │   ├── gacha.py              # POST /gacha/{session_id} — reshuffle picks
│   │   ├── history.py            # GET /history, GET /history/team, POST /history (with month filter)
│   │   ├── pair.py               # POST /pair, GET /me, POST /logout — web session management
│   │   ├── recommend.py          # POST /recommend — restaurant recommendation
│   │   ├── restaurants.py        # CRUD /restaurants + search + POST /restaurants/sync-from-maps
│   │   └── telegram.py           # POST /webhook/telegram — Telegram bot webhook
│   │
│   ├── bot/                      # Telegram bot framework
│   │   ├── application.py        # Bot app setup (python-telegram-bot v20+, async)
│   │   ├── poll_timeout.py       # Background poll expiry checker (complete + announce winner)
│   │   ├── handlers/             # Command handlers
│   │   │   ├── attendance.py      # /wfh and /in — attendance status commands
│   │   │   ├── blacklist.py      # /blacklist add|list|remove — manage restaurant blacklist
│   │   │   ├── gacha_solo.py     # /gacha — solo random pick with confirm/reroll flow
│   │   │   ├── lunch.py          # /lunch — recommend restaurants, create poll with inline keyboard
│   │   │   ├── restaurant_cmd.py  # /addrestaurant + /editrestaurant — ConversationHandler multi-step flows
│   │   │   ├── poll_callbacks.py # Callback handlers: vote, cancel, gacha, skip button presses
│   │   │   ├── start.py          # /start — user registration + pairing token
│   │   │   ├── help.py           # /help — list all commands
│   │   │   └── unknown.py        # Unknown command fallback
│   │   └── utils/                # Bot utilities (keyboards, formatters)
│   │
│   ├── services/                 # Business logic — core processing, external API calls
│   │   ├── attendance_repo.py    # Attendance CRUD (set_status, get_today, get_attendees, drop_unknown)
│   │   ├── blacklist_repo.py     # Blacklist CRUD (add, remove, list, get_ids, cleanup_expired)
│   │   ├── gacha.py              # Gacha roll logic (reshuffle from pool, limit 5 rolls)
│   │   ├── google_maps.py        # Google Maps Places API (search_nearby, get_photo_url)
│   │   ├── history_repo.py       # Lunch history CRUD (log_lunch, get_recent, user/team history)
│   │   ├── pairing_repo.py       # Pairing token CRUD (create, validate, consume, cleanup)
│   │   ├── poll_repo.py          # Poll CRUD (create, vote, counts, winner, expire, cancel, complete)
│   │   ├── web_session_repo.py   # Web session CRUD (create, validate, delete, cleanup)
│   │   ├── recommendation.py     # Quality-threshold filter + uniform random pool (keeps gacha session shape)
│   │   ├── restaurant_repo.py    # Restaurant CRUD operations (upsert, list, update, delete)
│   │   ├── session_pool.py       # In-memory session pool cache (create, get, expire, TTL 2hr)
│   │   └── user_repo.py          # User upsert by telegram_id
│   │
│   ├── models/                   # SQLAlchemy ORM models — database table definitions
│   │   ├── attendance.py         # UserAttendance model (user_id, date, status) + AttendanceStatus enum
│   │   ├── lunch_history.py      # LunchHistory model (restaurant_id, date, attendees)
│   │   ├── pairing_token.py      # PairingToken model (token, user_id, expires_at, consumed_at)
│   │   ├── poll.py               # PollSession + PollVote models, PollStatus enum (ACTIVE/COMPLETED/CANCELLED)
│   │   ├── web_session.py        # WebSession model (user_id, session_token, expires_at)
│   │   ├── restaurant.py         # Restaurant model + RestaurantSource enum
│   │   ├── user.py               # User model (telegram_id, name)
│   │   └── user_blacklist.py     # UserBlacklist model (user_id, restaurant_id, mode, expires_at)
│   │
│   ├── schemas/                  # Pydantic schemas — request/response validation
│   │   ├── google_maps.py        # Google Maps API response schema
│   │   ├── blacklist.py           # BlacklistAddRequest, BlacklistResponse
│   │   ├── gacha.py              # GachaResult
│   │   ├── history.py            # LogLunchRequest, LunchHistoryResponse
│   │   ├── recommendation.py     # RecommendRequest, RecommendationResult
│   │   └── restaurant.py         # RestaurantResponse, ManualRestaurantCreate, RestaurantUpdate
│   │
│   └── utils/                    # Shared utility functions
│
├── tests/                        # Test suite
│   └── unit/                     # Unit tests
│       ├── test_blacklist.py      # Blacklist repo + API + recommendation filter tests (21 cases)
│       ├── test_gacha.py         # Session pool + gacha roll + API tests (20 cases)
│       ├── test_google_maps.py   # Google Maps service tests (10 cases)
│       ├── test_health.py        # Health endpoint test (1 case)
│       ├── test_history.py       # History repo + API + recommendation filter tests (19 cases)
│       ├── test_recommendation.py # Recommendation pipeline tests (20 cases)
│       ├── test_restaurant_repo.py # Restaurant repo upsert tests (2 cases)
│       ├── test_restaurants.py   # Restaurant CRUD + API tests (18 cases)
│       ├── test_config.py        # Settings/config tests (2 cases)
│       ├── test_attendance.py    # Attendance repo + handlers + API tests (16 cases)
│       ├── test_blacklist_bot.py  # Blacklist bot commands: add/list/remove + callbacks (14 cases)
│       ├── test_gacha_bot.py    # Gacha bot integration: vote reset, solo /gacha handler (7 cases)
│       ├── test_restaurant_cmd.py # Add/edit restaurant conversation handlers (18 cases)
│       ├── test_lunch_poll.py   # Poll repo + lunch handler + vote/cancel/timeout tests (24 cases)
│       ├── test_telegram_bot.py  # Bot handlers + webhook + user/pairing repo tests (22 cases)
│       ├── test_pair.py          # Pairing endpoint + session management tests (16 cases)
│       └── test_web_features.py  # Restaurant search + history month filter + enriched responses (13 cases)
│
├── alembic/                      # Database migrations
│   ├── env.py                    # Alembic config
│   └── versions/                 # Migration files
│       ├── 995ad0e072c8_...py    # Create users + restaurants tables
│       ├── 1991e2f3d3bc_...py    # Create lunch_history table
│       ├── 855e8189a896_...py    # Create user_blacklist table
│       ├── 7b1ab9603757_...py    # Create pairing_tokens table
│       ├── ef50f8b44f33_...py    # Create user_attendance table
│       ├── a367868b9af9_...py    # Create poll_sessions + poll_votes tables
│       ├── b1c2d3e4f5a6_...py    # Create web_sessions table
│       └── c7d8e9f0a1b2_...py    # Add user_ratings_total to restaurants
│
├── scripts/                      # Utility scripts
│   ├── check_db.py               # DB connection check
│   ├── run_polling.py            # Run bot in polling mode (local dev) with timeout loop
│   └── setup_webhook.py          # Set up Telegram bot webhook
│
├── alembic.ini                   # Alembic settings
├── requirements.txt              # Production dependencies
└── requirements-dev.txt          # Dev/test dependencies (pytest, etc.)
```

## Architecture (3-layer)

```
Client Request
      │
      ▼
  api/  ─── Controller layer: validate input, return response
      │
      ▼
  services/  ─── Business logic: processing, external APIs, DB operations
      │
      ▼
  models/  ─── Data layer: SQLAlchemy ORM table definitions
```

## Key Patterns

- **Pydantic schemas** validate all request/response data (`schemas/`)
- **Dependency injection** for DB sessions via `Depends(get_db)`
- **Repository pattern** in `restaurant_repo.py` for DB operations
- **Alembic** manages database migrations (like Prisma Migrate for Python)
- **SQLAlchemy ORM** maps Python classes to PostgreSQL tables
- **python-telegram-bot** v20+ async framework for Telegram bot commands
- **Webhook** receives Telegram updates via `POST /webhook/telegram`
