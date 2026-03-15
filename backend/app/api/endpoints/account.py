from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.api.deps import get_current_user, get_db
from backend.app.models.user import User, Role
from backend.app.schemas.user import UserCreate, UserOut
from backend.app.services.user_service import create_user_with_password, update_password
from backend.app.services.email_service import send_credentials_email
import secrets
import string

router = APIRouter()


def _generate_password(length: int = 12) -> str:
    # Génère un mot de passe aléatoire alphanumérique + caractères spéciaux
    alphabet = string.ascii_letters + string.digits + "!@#$%"
    return "".join(secrets.choice(alphabet) for _ in range(length))


@router.post("/create", response_model=UserOut, status_code=status.HTTP_201_CREATED, summary="Créer un compte utilisateur (admin seulement)")
def create_account(payload: UserCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Seuls les admins peuvent créer des comptes
    if current_user.role != Role.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Réservé aux administrateurs.")

    # Empêche la création d'un compte avec un email déjà existant
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"L'adresse {payload.email} est déjà utilisée.")

    # Génère un mot de passe temporaire et crée le compte
    password = _generate_password()
    user = create_user_with_password(db=db, user_in=payload, password=password)

    # Envoie les identifiants par email — non bloquant si le serveur SMTP est indisponible
    try:
        send_credentials_email(to_email=user.email, first_name=user.first_name, role=payload.role, plain_password=password)
    except Exception:
        pass  # la création du compte réussit même si l'email échoue

    return user


@router.post("/change-password", summary="Changer son mot de passe (première connexion ou renouvellement)")
def change_password(payload: dict, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    new_password = payload.get("new_password", "")
    if len(new_password) < 8:
        # Validation minimale de longueur avant hashage
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Le mot de passe doit contenir au moins 8 caractères.")
    update_password(db=db, user=current_user, new_password=new_password)
    return {"message": "Mot de passe mis à jour avec succès."}


@router.get("/users", response_model=list[UserOut], summary="Lister tous les utilisateurs (admin seulement)")
def list_users(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Retourne tous les comptes triés par date de création décroissante
    if current_user.role != Role.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Réservé aux administrateurs.")
    return db.query(User).order_by(User.created_at.desc()).all()
