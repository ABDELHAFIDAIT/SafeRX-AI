from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.api.deps import get_current_user, get_db
from backend.app.models.user import User, Role
from backend.app.services.lr_service import train, get_lr_status
from backend.app.services.ai_service import get_ai_status

router = APIRouter()


@router.post("/train", summary="Entraîner la Logistic Regression sur l'historique d'audit (admin)", status_code=status.HTTP_200_OK)
def train_model(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Réservé aux admins — lance l'entraînement du modèle LR sur audit_cds_hooks
    if current_user.role != Role.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Réservé aux administrateurs.")
    result = train(db)
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["detail"])  # scikit-learn absent
    return result


@router.get("/status", summary="Statut des modules IA (Logistic Regression + RAG)")
def ai_status(current_user: User = Depends(get_current_user)):
    # Retourne l'état combiné du modèle LR et du provider RAG actif
    return {
        "logistic_regression": get_lr_status(),
        "rag":                 get_ai_status(),
    }
