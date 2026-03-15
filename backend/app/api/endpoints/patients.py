from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.api.deps import get_current_user, get_db
from backend.app.models.patient import Patient
from backend.app.models.user import User, Role
from backend.app.schemas.clinical_schemas import PatientCreate, PatientOut, PatientUpdate

router = APIRouter()

# Rôles autorisés à accéder aux dossiers patients
_ALLOWED_ROLES = (Role.DOCTOR, Role.PHARMACIST, Role.ADMIN)


@router.post("/", response_model=PatientOut, status_code=status.HTTP_201_CREATED, summary="Créer un dossier patient")
def create_patient(payload: PatientCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role not in _ALLOWED_ROLES:
        raise HTTPException(status_code=403, detail="Accès refusé.")
    patient = Patient(**payload.model_dump())  # crée l'objet ORM directement depuis le schema validé
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient


@router.get("/{patient_id}", response_model=PatientOut, summary="Récupérer un dossier patient")
def get_patient(patient_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role not in _ALLOWED_ROLES:
        raise HTTPException(status_code=403, detail="Accès refusé.")
    patient = db.query(Patient).get(patient_id)
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Patient {patient_id} introuvable.")
    return patient


@router.patch("/{patient_id}", response_model=PatientOut, summary="Mettre à jour un dossier patient")
def update_patient(patient_id: int, payload: PatientUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role not in _ALLOWED_ROLES:
        raise HTTPException(status_code=403, detail="Accès refusé.")
    patient = db.query(Patient).get(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail=f"Patient {patient_id} introuvable.")

    # Applique uniquement les champs explicitement envoyés (patch partiel)
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(patient, field, value)

    db.commit()
    db.refresh(patient)
    return patient


@router.get("/", response_model=list[PatientOut], summary="Lister les patients")
def list_patients(skip: int = 0, limit: int = 50, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role not in _ALLOWED_ROLES:
        raise HTTPException(status_code=403, detail="Accès refusé.")
    return db.query(Patient).offset(skip).limit(limit).all()
