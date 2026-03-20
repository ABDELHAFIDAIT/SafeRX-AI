from fastapi import APIRouter
from backend.app.api.endpoints import (
    auth,
    account,
    patients,
    prescriptions,
    drugs,
    audit,
    ai,
)

router = APIRouter()

router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(account.router, prefix="/account", tags=["account"])
router.include_router(patients.router, prefix="/patients", tags=["patients"])
router.include_router(
    prescriptions.router, prefix="/prescriptions", tags=["prescriptions"]
)
router.include_router(drugs.router, prefix="/drugs", tags=["drugs"])
router.include_router(audit.router, prefix="/audit", tags=["Audit"])
router.include_router(ai.router, prefix="/ai", tags=["AI"])
