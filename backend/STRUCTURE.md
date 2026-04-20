# PICK Backend — Project Structure

```
backend/
├── app/                          # Application source code
│   ├── main.py                   # FastAPI app entry point, registers all routers
│   ├── config.py                 # Environment config (DATABASE_URL, API keys, bot token)
│   ├── database.py               # SQLAlchemy engine, session factory, get_db dependency
│   │
│   ├── api/                      # API layer — receives HTTP requests, returns responses
│   │   ├── blacklist.py          # POST /blacklist, DELETE /blacklist/{id}, GET /blacklist
│   │   ├── dev.py                # Developer/debug endpoints
│   │   ├── gacha.py              # POST /gacha/{session_id} — reshuffle picks
│   │   ├── history.py            # GET /history, GET /history/team, POST /history
│   │   ├── recommend.py          # POST /recommend — restaurant recommendation
│   │   ├── restaurants.py        # CRUD /restaurants + POST /restaurants/sync-from-maps
│   │   └── telegram.py           # POST /webhook/telegram — Telegram bot webhook
│   │
│   ├── bot/                      # Telegram bot framework
│   │   ├── application.py        # Bot app setup (python-telegram-bot v20+, async)
│   │   ├── handlers/             # Command handlers
│   │   │   ├── start.py          # /start — user registration + pairing token
│   │   │   ├── help.py           # /help — list all commands
│   │   │   └── unknown.py        # Unknown command fallback
│   │   └── utils/                # Bot utilities (keyboards, formatters)
│   │
│   ├── services/                 # Business logic — core processing, external API calls
│   │   ├── blacklist_repo.py     # Blacklist CRUD (add, remove, list, get_ids, cleanup_expired)
│   │   ├── gacha.py              # Gacha roll logic (reshuffle from pool, limit 5 rolls)
│   │   ├── google_maps.py        # Google Maps Places API (search_nearby, get_photo_url)
│   │   ├── history_repo.py       # Lunch history CRUD (log_lunch, get_recent, user/team history)
│   │   ├── pairing_repo.py       # Pairing token CRUD (create, validate, consume, cleanup)
│   │   ├── recommendation.py     # 5-stage recommendation pipeline (with history + blacklist filter)
│   │   ├── restaurant_repo.py    # Restaurant CRUD operations (upsert, list, update, delete)
│   │   ├── session_pool.py       # In-memory session pool cache (create, get, expire, TTL 2hr)
│   │   └── user_repo.py          # User upsert by telegram_id
│   │
│   ├── models/                   # SQLAlchemy ORM models — database table definitions
│   │   ├── lunch_history.py      # LunchHistory model (restaurant_id, date, attendees)
│   │   ├── pairing_token.py      # PairingToken model (token, user_id, expires_at, consumed_at)
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
│       ├── test_recommendation.py # Recommendation pipeline tests (19 cases)
│       ├── test_restaurants.py   # Restaurant CRUD + API tests (18 cases)
│       └── test_telegram_bot.py  # Bot handlers + webhook + user/pairing repo tests (22 cases)
│
├── alembic/                      # Database migrations
│   ├── env.py                    # Alembic config
│   └── versions/                 # Migration files
│       ├── 995ad0e072c8_...py    # Create users + restaurants tables
│       ├── 1991e2f3d3bc_...py    # Create lunch_history table
│       ├── 855e8189a896_...py    # Create user_blacklist table
│       └── 7b1ab9603757_...py    # Create pairing_tokens table
│
├── scripts/                      # Utility scripts
│   ├── check_db.py               # DB connection check
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
