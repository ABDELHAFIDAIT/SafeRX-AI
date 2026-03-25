from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from backend.app.core import security
from backend.app.core.config import settings
from backend.app.api.deps import get_db
from backend.app.services import user_service

router = APIRouter()


@router.post("/login")
def login(
    db: Session = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends(),
):
    """
    Endpoint de connexion — authentifie un utilisateur avec email/mot de passe.
    
    Retourne:
        - access_token: JWT signé (Bearer)
        - token_type: "bearer"
        - is_first_login: Flag indiquant si le mot de passe doit être changé
        - role: Rôle de l'utilisateur (admin, doctor, pharmacist)
        - first_name et last_name: Nom et prénom
    """
    # Recherche l'utilisateur et vérifie le mot de passe
    user = user_service.get_user_by_email(db, email=form_data.username)
    if not user or not security.verify_password(form_data.password, user.password):
        # Identifiants invalides — message générique pour la sécurité
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nom d'utilisateur ou mot de passe incorrect",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Crée un JWT avec expiration configurée
    access_token_expires = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        subject=user.email, expires_delta=access_token_expires
    )

    # Inclut is_first_login pour rediriger le frontend vers le changement de mot de passe
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "is_first_login": user.is_first_login,
        "role": user.role.value,
        "first_name": user.first_name,
        "last_name": user.last_name,
    }
