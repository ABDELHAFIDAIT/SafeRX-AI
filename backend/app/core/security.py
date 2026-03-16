from datetime import datetime, timedelta, timezone
from typing import Any, Union
from jose import jwt
from passlib.context import CryptContext
from backend.app.core.config import settings


pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")  # algorithme de hashage argon2


def verify_password(plain_password: str, hashed_password: str) :
    # Vérifie un mot de passe en clair contre son hash argon2
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) :
    # Retourne le hash argon2 d'un mot de passe en clair
    return pwd_context.hash(password)


def create_access_token(subject: Union[str, Any], expires_delta: timedelta = None) :
    # Crée un JWT signé avec l'email en "sub" et une expiration configurable
    if expires_delta :
        expire = datetime.now(timezone.utc) + expires_delta 
    else :
        expire = datetime.now(timezone.utc) + timedelta(minutes=100)  # durée par défaut si non fournie
    
    to_encode = {"exp": expire, "sub": subject}
    
    encoded_jwt = jwt.encode(to_encode, key=settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    
    return encoded_jwt