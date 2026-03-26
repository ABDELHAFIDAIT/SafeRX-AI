from __future__ import annotations
import uuid as _uuid
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from backend.app.api.deps import get_current_user, get_db
from backend.app.models.patient import Patient
from backend.app.models.user import User, Role
from backend.app.schemas.clinical_schemas import (
    PatientCreate,
    PatientOut,
    PatientUpdate,
)


router = APIRouter()


def _payload_to_dict(payload: PatientCreate) -> dict:
    """
    Convertit le payload Pydantic en dict compatible SQLAlchemy.
    - fhir_patient_id : uuid.UUID → str  (la colonne SQLAlchemy est String)
    - Les float et bool sont déjà natifs
    """
    data = payload.model_dump()
    if data.get("fhir_patient_id") is not None:
        data["fhir_patient_id"] = str(data["fhir_patient_id"])
    return data


# ─────────────────────────────────────────────────────────────────────────────
#  POST / — Créer un dossier patient
# ─────────────────────────────────────────────────────────────────────────────


@router.post(
    "/",
    response_model=PatientOut,
    status_code=status.HTTP_201_CREATED,
    summary="Créer un dossier patient",
)
def create_patient(
    payload: PatientCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in (Role.DOCTOR, Role.PHARMACIST, Role.ADMIN):
        raise HTTPException(status_code=403, detail="Accès refusé.")

    patient = Patient(**_payload_to_dict(payload))
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient


# ─────────────────────────────────────────────────────────────────────────────
#  GET /search — AVANT /{patient_id} pour éviter le conflit de route
# ─────────────────────────────────────────────────────────────────────────────


@router.get(
    "/search",
    response_model=list[PatientOut],
    summary="Rechercher un patient par ID numérique ou FHIR UUID",
)
def search_patients(
    q: str = Query(..., min_length=1, description="ID numérique ou FHIR UUID"),
    limit: int = Query(default=10, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # ID numérique
    try:
        patient_id = int(q.strip())
        p = db.query(Patient).filter(Patient.id == patient_id).first()
        return [p] if p else []
    except ValueError:
        pass

    # FHIR UUID — on compare en str car la colonne est String
    try:
        fhir_id = str(_uuid.UUID(q.strip()))
        p = db.query(Patient).filter(Patient.fhir_patient_id == fhir_id).first()
        return [p] if p else []
    except ValueError:
        pass

    return []


# ─────────────────────────────────────────────────────────────────────────────
#  GET / — Lister les patients
# ─────────────────────────────────────────────────────────────────────────────


@router.get(
    "/",
    response_model=list[PatientOut],
    summary="Lister les patients",
)
def list_patients(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(Patient).offset(skip).limit(limit).all()


# ─────────────────────────────────────────────────────────────────────────────
#  GET /{patient_id} — APRÈS /search et /
# ─────────────────────────────────────────────────────────────────────────────


@router.get(
    "/{patient_id}",
    response_model=PatientOut,
    summary="Récupérer un dossier patient",
)
def get_patient(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    patient = db.query(Patient).get(patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient {patient_id} introuvable.",
        )
    return patient


# ─────────────────────────────────────────────────────────────────────────────
#  PATCH /{patient_id} — Mettre à jour un dossier patient
# ─────────────────────────────────────────────────────────────────────────────


@router.patch(
    "/{patient_id}",
    response_model=PatientOut,
    summary="Mettre à jour un dossier patient",
)
def update_patient(
    patient_id: int,
    payload: PatientUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    patient = db.query(Patient).get(patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient {patient_id} introuvable.",
        )

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(patient, field, value)

    db.commit()
    db.refresh(patient)
    return patient
