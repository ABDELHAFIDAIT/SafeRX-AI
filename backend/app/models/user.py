from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, Enum, DateTime
from backend.app.db.base import Base
from enum import Enum as PyEnum


class Role(str, PyEnum):
    """
    Rôles d'accès à la plateforme SafeRx AI.
    Contrôlent les droits d'accès aux endpoints et fonctionnalités.
    """
    ADMIN = "admin"              # Administrateur — accès complet
    DOCTOR = "doctor"            # Médecin prescripteur
    PHARMACIST = "pharmacist"    # Pharmacien validateur


class User(Base):
    """
    Compte utilisateur de la plateforme SafeRx AI.
    Stocke les identifiants de connexion et métadonnées de compte.
    """
    __tablename__ = "users"

    # Identifiant unique et clé primaire
    id = Column(Integer, primary_key=True, index=True)
    
    # Informations d'identité de l'utilisateur
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    
    # Email unique — utilisé comme identifiant de connexion
    email = Column(String, nullable=False, unique=True, index=True)
    
    # Mot de passe haché avec argon2 (jamais stocké en clair)
    password = Column(String, nullable=False)
    
    # Rôle de l'utilisateur (admin, doctor, pharmacist)
    role = Column(Enum(Role), nullable=False)
    
    # Statut du compte (active = True, désactivé = False)
    is_active = Column(Boolean, default=True)
    
    # Flag obligeant à changer le password à la première connexion
    is_first_login = Column(Boolean, default=True)
    
    # Horodatage automatique de création et modification
    created_at = Column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
