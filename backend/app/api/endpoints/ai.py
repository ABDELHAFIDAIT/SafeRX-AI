from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.api.deps import get_current_user, get_db
from backend.app.models.user import User, Role
from backend.app.services.ai_service import get_ai_status


router = APIRouter()


@router.get("/status", summary="Statut des modules IA (Logistic Regression + RAG)")
def ai_status(current_user: User = Depends(get_current_user)):
    # Retourne l'état combiné du modèle LR et du provider RAG actif
    return {
        "rag": get_ai_status(),
    }
