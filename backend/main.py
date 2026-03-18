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
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_client import Counter, Histogram


# Alertes CDS générées par le moteur de règles
CDS_ALERTS_TOTAL = Counter(
    "saferx_cds_alerts_total",
    "Nombre d'alertes CDS générées",
    ["alert_type", "severity"],
)
 
# Alertes enrichies par le RAG (LLM a fourni une explication)
RAG_ENRICHED_TOTAL = Counter(
    "saferx_rag_enriched_total",
    "Alertes enrichies par le LLM (RAG)",
    ["alert_type"],
)
 
# Décisions des médecins face aux alertes
AUDIT_DECISIONS_TOTAL = Counter(
    "saferx_audit_decisions_total",
    "Décisions médecin : ACCEPTED / IGNORED / OVERRIDE",
    ["decision", "alert_type", "severity"],
)
 
# Prescriptions créées (safe = 0 alerte, alerts = au moins 1 alerte)
PRESCRIPTIONS_TOTAL = Counter(
    "saferx_prescriptions_total",
    "Prescriptions créées, par statut",
    ["status"],
)

 
def record_cds_alerts(alerts: list) -> None:
    for alert in alerts:
        CDS_ALERTS_TOTAL.labels(
            alert_type=alert.alert_type or "UNKNOWN",
            severity=alert.severity or "UNKNOWN",
        ).inc()

        if alert.rag_explanation:
            RAG_ENRICHED_TOTAL.labels(
                alert_type=alert.alert_type or "UNKNOWN"
            ).inc()
 
 
def record_prescription(status: str) -> None:
    PRESCRIPTIONS_TOTAL.labels(status=status).inc()
 
 
def record_audit_decision(decision: str, alert_type: str, severity: str) -> None:
    AUDIT_DECISIONS_TOTAL.labels(
        decision=decision,
        alert_type=alert_type or "UNKNOWN",
        severity=severity or "UNKNOWN",
    ).inc()


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


Instrumentator(
    should_group_status_codes=False, 
    should_ignore_untemplated=True,  
    excluded_handlers=["/metrics", "/"],
).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

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
