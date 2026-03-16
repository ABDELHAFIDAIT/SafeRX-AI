"""
SafeRx AI — Endpoints /prescriptions
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import  Session

from backend.app.api.deps import get_current_user, get_db
from backend.app.models.user import User, Role
from backend.app.schemas.clinical_schemas import (
    CdsResponse,
    PrescriptionCreate,
    PrescriptionOut,
)
from backend.app.services.prescription_service import (
    create_prescription,
    get_prescription,
    list_prescriptions_for_patient,
)

router = APIRouter()


# ─────────────────────────────────────────────────────────────────────────────
#  POST /prescriptions
#  Crée une prescription + analyse CDS instantanée
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/",
    response_model=CdsResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer une prescription et déclencher l'analyse CDS",
)
def create_prescription_endpoint(
    payload: PrescriptionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Accessible aux médecins et pharmaciens.
    Crée la prescription, analyse chaque ligne de médicament et retourne
    les alertes détectées (interactions, allergies, contre-indications…).
    """
    if current_user.role not in (Role.DOCTOR, Role.PHARMACIST):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seuls les médecins et pharmaciens peuvent créer des prescriptions.",
        )

    try:
        prescription = create_prescription(
            db=db, payload=payload, doctor=current_user
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )

    # Aplatir toutes les alertes pour la réponse CDS
    all_alerts = [
        alert
        for line in prescription.lines
        for alert in line.alerts
    ]

    return CdsResponse(
        prescription_id=prescription.id,
        status=prescription.status,           # "safe" | "alerts"
        alert_count=len(all_alerts),
        alerts=all_alerts,
        prescription=prescription,
    )


# ─────────────────────────────────────────────────────────────────────────────
#  GET /prescriptions/{id}
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/{prescription_id}",
    response_model=CdsResponse,
    summary="Récupérer une prescription avec ses alertes",
)
def get_prescription_endpoint(
    prescription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    prescription = get_prescription(db=db, prescription_id=prescription_id)
    if not prescription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prescription {prescription_id} introuvable.",
        )

    all_alerts = [
        alert
        for line in prescription.lines
        for alert in line.alerts
    ]

    return CdsResponse(
        prescription_id=prescription.id,
        status=prescription.status,
        alert_count=len(all_alerts),
        alerts=all_alerts,
        prescription=prescription,
    )


# ─────────────────────────────────────────────────────────────────────────────
#  GET /prescriptions/patient/{patient_id}
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/patient/{patient_id}",
    response_model=list[PrescriptionOut],
    summary="Lister les prescriptions d'un patient",
)
def list_patient_prescriptions(
    patient_id: int,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_prescriptions_for_patient(
        db=db, patient_id=patient_id, skip=skip, limit=limit
    )


# ─────────────────────────────────────────────────────────────────────────────
#  GET /prescriptions/doctor/mine — Prescriptions du médecin connecté
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/doctor/mine",
    response_model=list[PrescriptionOut],
    summary="Prescriptions créées par le médecin connecté (plus récentes en premier)",
)
def get_my_prescriptions(
    skip:  int = Query(default=0),
    limit: int = Query(default=30, le=100),
    db:    Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from backend.app.models.prescription import Prescription, PrescriptionLine
    from sqlalchemy.orm import selectinload

    return (
        db.query(Prescription)
        .options(selectinload(Prescription.lines).selectinload(PrescriptionLine.alerts))
        .filter(Prescription.doctor_id == current_user.id)
        .order_by(Prescription.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )