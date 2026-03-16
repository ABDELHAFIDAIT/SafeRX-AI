"""
SafeRx AI — Endpoints /patients
Gestion des dossiers patients (données fictives Synthea uniquement).

⚠️  ORDRE DES ROUTES IMPORTANT (FastAPI évalue dans l'ordre de déclaration) :
    GET /search   doit être défini AVANT GET /{patient_id}
    sinon "search" est interprété comme un patient_id entier → 422
"""

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

    patient = Patient(**payload.model_dump())
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
    """
    Recherche flexible :
    - Si q est un entier → cherche par Patient.id exact
    - Si q ressemble à un UUID → cherche par fhir_patient_id
    - Sinon → retourne liste vide (RGPD : pas de recherche par nom)
    """
    # Essai : ID numérique
    try:
        patient_id = int(q.strip())
        p = db.query(Patient).filter(Patient.id == patient_id).first()
        return [p] if p else []
    except ValueError:
        pass

    # Essai : FHIR UUID
    try:
        fhir_id = _uuid.UUID(q.strip())
        p = db.query(Patient).filter(Patient.fhir_patient_id == str(fhir_id)).first()
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
#  GET /{patient_id} — ⚠️  APRÈS /search et / pour éviter les conflits
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

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(patient, field, value)

    db.commit()
    db.refresh(patient)
    return patient
