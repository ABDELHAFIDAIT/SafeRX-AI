from backend.app.db.session import SessionLocal
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from backend.app.core.config import settings
from backend.app.services import user_service
from backend.app.models.user import Role, User

# Schéma OAuth2 — pointe vers l'endpoint de login pour la documentation Swagger
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_STR}/auth/login")


def get_db():
    """
    Générateur de session SQLAlchemy — crée et ferme une session pour chaque requête.
    Garantit la fermeture même en cas d'erreur (via finally).
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)
) -> User:
    """
    Dépendance FastAPI — décode le JWT et retourne l'utilisateur correspondant.
    Lève une exception 401 si le token est invalide ou l'utilisateur inexistant.
    
    Args:
        db: Session de base de données
        token: JWT extrait de l'en-tête Authorization
    
    Returns:
        Utilisateur authentifié
    
    Raises:
        HTTPException 401 si le token est invalide ou l'utilisateur inexistant
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Impossible de valider les informations d'identification",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Décode le JWT avec la clé secrète et l'algorithme configurés
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        email: str = payload.get("sub")  # "sub" contient l'email
        if email is None:
            raise credentials_exception
    except JWTError:
        # Token expiré, mal formé, ou signé avec la mauvaise clé
        raise credentials_exception

    # Cherche l'utilisateur en base de données
    user = user_service.get_user_by_email(db, email)
    if user is None:
        # Token valide mais utilisateur supprimé entre-temps
        raise credentials_exception

    return user


def get_current_active_admin(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> User:
    """
    Dépendance FastAPI — vérifie que l'utilisateur courant a le rôle ADMIN.
    Utilisée pour protéger les endpoints réservés aux administrateurs.
    
    Args:
        db: Session de base de données
        current_user: Utilisateur extrait de get_current_user
    
    Returns:
        Utilisateur ADMIN
    
    Raises:
        HTTPException 403 si l'utilisateur n'est pas ADMIN
    """
    if current_user.role != Role.ADMIN:
        raise HTTPException(
            status_code=403, detail="Accès refusé : privilèges d'administrateur requis"
        )
    return current_user
