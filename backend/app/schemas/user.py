from pydantic import BaseModel, ConfigDict, EmailStr
from typing import Optional
from backend.app.models.user import Role
from datetime import datetime


class UserBase(BaseModel):
    first_name: str
    last_name:  str
    email:      EmailStr
    role:       Role


class UserCreate(UserBase):
    # Mot de passe optionnel — si absent, il sera généré automatiquement par l'admin
    password: Optional[str] = None


class UserUpdate(BaseModel):
    # Mise à jour partielle du profil utilisateur par l'admin
    first_name: Optional[str]  = None
    last_name:  Optional[str]  = None
    password:   Optional[str]  = None
    is_active:  Optional[bool] = None


class UserOut(UserBase):
    # Schéma de réponse — exclut le mot de passe, expose les métadonnées de compte
    id:             int
    is_active:      bool
    is_first_login: bool    # True si le mot de passe n'a pas encore été changé
    created_at:     datetime
    updated_at:     datetime

    model_config = ConfigDict(from_attributes=True)