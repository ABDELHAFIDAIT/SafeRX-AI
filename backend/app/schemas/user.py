from pydantic import BaseModel, ConfigDict, EmailStr
from typing import Optional
from backend.app.models.user import Role
from datetime import datetime


class UserBase(BaseModel):
    """Base schema pour les utilisateurs — fields communs à tous les schemas User."""
    first_name: str
    last_name: str
    email: EmailStr
    role: Role


class UserCreate(UserBase):
    """Payload pour la création d'un utilisateur — mot de passe optionnel (généré par l'admin si absent)."""
    password: Optional[str] = None


class UserUpdate(BaseModel):
    """Payload pour la mise à jour partielle d'un utilisateur par l'admin."""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None


class UserOut(UserBase):
    """Schéma de réponse — exclut le mot de passe, expose métadonnées de compte."""
    id: int
    is_active: bool
    is_first_login: bool  # True = mot de passe n'a pas encore été changé
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
