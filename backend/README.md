# Pick — Backend

FastAPI backend for the Pick food recommendation service.

## Requirements

- Python 3.11+
- PostgreSQL (Railway)

## Setup

```bash
# Install dependencies
pip install -r requirements.txt -r requirements-dev.txt

# Copy env and fill in values
cp .env.example .env
# Edit .env: set DATABASE_URL and GOOGLE_MAPS_API_KEY

# Run migrations
alembic upgrade head

# Start dev server
uvicorn app.main:app --reload
```

## Verify

```bash
curl http://localhost:8000/health
# {"status":"ok"}
```

## Test

```bash
pytest tests/
```
