from datetime import datetime, timedelta, timezone
from typing import Any, Union
from jose import jwt
from passlib.context import CryptContext
from backend.app.core.config import settings

# Contexte de hachage des mots de passe avec l'algorithme argon2 (sécurisé et adapté au hachage de MDP)
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Vérifie qu'un mot de passe en clair correspond à son hash argon2.
    
    Args:
        plain_password: Mot de passe en clair saisi par l'utilisateur
        hashed_password: Hash stocké en base de données
    
    Returns:
        True si le mot de passe est valide, False sinon
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hache un mot de passe en clair avec argon2.
    
    Args:
        password: Mot de passe à hacher
    
    Returns:
        Hash argon2 du mot de passe (stockable en base de données)
    """
    return pwd_context.hash(password)


def create_access_token(subject: Union[str, Any], expires_delta: timedelta = None) -> str:
    """
    Crée un JWT signé avec l'email en claim "sub" et une expiration configurable.
    
    Args:
        subject: Contenu du claim "sub" (généralement l'email de l'utilisateur)
        expires_delta: Durée de validité personnalisée (par défaut 100 minutes)
    
    Returns:
        JWT encodé et signé
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=100)

    to_encode = {"exp": expire, "sub": subject}
    encoded_jwt = jwt.encode(
        to_encode, key=settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt
