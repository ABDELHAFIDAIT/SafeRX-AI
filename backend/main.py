from fastapi import FastAPI
from backend.app.core.config import settings
from backend.app.api.router import router
from backend.app.db.session import SessionLocal
from backend.app.db.base import Base
from backend.app.db.session import engine
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from backend.app.db.init_db import init_db
from backend.app.models import user
from backend.app.models import drug


Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    db = SessionLocal()
    try:
        init_db(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="API for SafeRx AI application",
    version=settings.VERSION,
    lifespan=lifespan
)


origins = ["http://localhost:5173"]


app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


app.include_router(router, prefix=settings.API_STR)


@app.get("/")
async def health():
    return {
        "status": "success",
        "message": "Welcome to SafeRx AI API",
        "version": settings.VERSION,
    }
