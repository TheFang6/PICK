import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.bot.poll_timeout import poll_expiry_loop
from app.config import settings
from app.api.attendance import router as attendance_router
from app.api.blacklist import router as blacklist_router
from app.api.dev import router as dev_router
from app.api.gacha import router as gacha_router
from app.api.history import router as history_router
from app.api.recommend import router as recommend_router
from app.api.restaurants import router as restaurants_router
from app.api.pair import router as pair_router
from app.api.telegram import router as telegram_router

@asynccontextmanager
async def lifespan(app):
    task = asyncio.create_task(poll_expiry_loop())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(title="Pick API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.allowed_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(attendance_router)
app.include_router(dev_router)
app.include_router(restaurants_router)
app.include_router(recommend_router)
app.include_router(history_router)
app.include_router(blacklist_router)
app.include_router(gacha_router)
app.include_router(pair_router)
app.include_router(telegram_router)


@app.get("/health")
def health():
    return {"status": "ok"}
