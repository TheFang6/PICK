from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.blacklist import router as blacklist_router
from app.api.dev import router as dev_router
from app.api.history import router as history_router
from app.api.recommend import router as recommend_router
from app.api.restaurants import router as restaurants_router

app = FastAPI(title="Pick API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dev_router)
app.include_router(restaurants_router)
app.include_router(recommend_router)
app.include_router(history_router)
app.include_router(blacklist_router)


@app.get("/health")
def health():
    return {"status": "ok"}
