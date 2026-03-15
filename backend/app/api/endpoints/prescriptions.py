from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.api.deps import get_current_user, get_db
from backend.app.models.user import User, Role
from backend.app.schemas.clinical_schemas import CdsResponse, PrescriptionCreate, PrescriptionOut
from backend.app.services.prescription_service import create_prescription, get_prescription, list_prescriptions_for_patient

router = APIRouter()


@router.post("/", response_model=CdsResponse, status_code=status.HTTP_201_CREATED, summary="Créer une prescription et déclencher l'analyse CDS")
def create_prescription_endpoint(
    payload: PrescriptionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Seuls les médecins et pharmaciens peuvent soumettre des prescriptions
    if current_user.role not in (Role.DOCTOR, Role.PHARMACIST):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Seuls les médecins et pharmaciens peuvent créer des prescriptions.")

    try:
        prescription = create_prescription(db=db, payload=payload, doctor=current_user)
    except ValueError as exc:
        # Les erreurs métier (patient introuvable, drug_id invalide) sont remontées en 422
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc))

    # Aplatit les alertes de toutes les lignes pour la réponse CDS consolidée
    all_alerts = [alert for line in prescription.lines for alert in line.alerts]

    return CdsResponse(
        prescription_id = prescription.id,
        status          = prescription.status,   # "safe" | "alerts"
        alert_count     = len(all_alerts),
        alerts          = all_alerts,
        prescription    = prescription,
    )


@router.get("/{prescription_id}", response_model=CdsResponse, summary="Récupérer une prescription avec ses alertes")
def get_prescription_endpoint(
    prescription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    prescription = get_prescription(db=db, prescription_id=prescription_id)
    if not prescription:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Prescription {prescription_id} introuvable.")

    all_alerts = [alert for line in prescription.lines for alert in line.alerts]

    return CdsResponse(
        prescription_id = prescription.id,
        status          = prescription.status,
        alert_count     = len(all_alerts),
        alerts          = all_alerts,
        prescription    = prescription,
    )


@router.get("/patient/{patient_id}", response_model=list[PrescriptionOut], summary="Lister les prescriptions d'un patient")
def list_patient_prescriptions(
    patient_id: int,
    skip:  int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Délègue la pagination au service — tri chronologique décroissant
    return list_prescriptions_for_patient(db=db, patient_id=patient_id, skip=skip, limit=limit)
