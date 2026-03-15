from fastapi import FastAPI
from backend.app.core.config import settings
from backend.app.api.router import router
from backend.app.db.session import SessionLocal
from backend.app.db.base import Base
from backend.app.db.session import engine
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from backend.app.db.init_db import init_db
from backend.app.models import user, drug, patient, prescription, cds_alert

# Crée toutes les tables si elles n'existent pas encore (migration simplifiée sans Alembic)
Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialise l'admin par défaut au démarrage de l'application
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
    lifespan=lifespan,
)

# Autorise uniquement le frontend de développement en CORS
origins = ["http://localhost:5173"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Monte tous les routers sous le préfixe défini dans settings.API_STR
app.include_router(router, prefix=settings.API_STR)


@app.get("/")
async def health():
    # Endpoint de santé — utilisé par les health checks Docker et les load balancers
    return {
        "status":  "success",
        "message": "Welcome to SafeRx AI API",
        "version": settings.VERSION,
    }
