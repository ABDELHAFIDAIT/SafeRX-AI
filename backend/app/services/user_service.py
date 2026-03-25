from sqlalchemy.orm import Session
from backend.app.models.user import User
from backend.app.schemas.user import UserCreate
from backend.app.core.security import get_password_hash
from datetime import datetime, timezone


def get_user_by_email(db: Session, email: str) -> User:
    """
    Recherche un utilisateur par son adresse email.
    Utilisé lors de l'authentification et de la vérification d'unicité.
    
    Args:
        db: Session SQLAlchemy
        email: Adresse email à chercher
    
    Returns:
        Objet User ou None si non trouvé
    """
    return db.query(User).filter(User.email == email).first()


def create_user(db: Session, user_in: UserCreate) -> User:
    """
    Crée un utilisateur avec mot de passe fourni et hashé.
    Usage interne — pour les créations spéciales sans gestion de first_login.
    
    Args:
        db: Session SQLAlchemy
        user_in: Schéma UserCreate contenant first_name, last_name, email, password, role
    
    Returns:
        Objet User créé et persisté
    """
    hashed_password = get_password_hash(user_in.password)
    user = User(
        first_name=user_in.first_name,
        last_name=user_in.last_name,
        email=user_in.email,
        password=hashed_password,
        role=user_in.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_user_with_password(db: Session, user_in: UserCreate, password: str) -> User:
    """
    Crée un utilisateur via l'admin avec mot de passe prescrit.
    Force is_first_login=True pour obliger le changement au login initial.
    
    Args:
        db: Session SQLAlchemy
        user_in: Schéma UserCreate
        password: Mot de passe en clair à hacher
    
    Returns:
        Objet User créé avec is_first_login=True
    """
    hashed_password = get_password_hash(password)
    db_user = User(
        first_name=user_in.first_name,
        last_name=user_in.last_name,
        email=user_in.email,
        password=hashed_password,
        role=user_in.role,
        is_first_login=True,
        is_active=True,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def update_password(db: Session, user: User, new_password: str) -> User:
    """
    Met à jour le mot de passe d'un utilisateur et désactive le flag first_login.
    
    Args:
        db: Session SQLAlchemy
        user: Objet User à modifier
        new_password: Nouveau mot de passe en clair
    
    Returns:
        Objet User modifié et persisté
    """
    user.password = get_password_hash(new_password)
    user.is_first_login = False
    user.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)
    return user
