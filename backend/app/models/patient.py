from sqlalchemy import (
    Column,
    Integer,
    String,
    Date,
    Numeric,
    Boolean,
    SmallInteger,
    ARRAY,
    Text,
    TIMESTAMP,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.app.db.base import Base


class Patient(Base):
    """
    Dossier patient — contient les données cliniques et anthropométriques.
    Utilisé par le moteur CDS pour générer les alertes de sécurité.
    """
    __tablename__ = "patients"

    # Identifiant unique
    id = Column(Integer, primary_key=True, index=True)
    
    # Identifiant FHIR externe (optionnel, pour intégration avec des systèmes externes)
    fhir_patient_id = Column(
        UUID(as_uuid=True), unique=True, nullable=True
    )
    
    # Date de naissance — pour calculer l'âge et vérifier l'âge minimal des médicaments
    birthdate = Column(Date, nullable=False)
    
    # Sexe du patient (M=Masculin, F=Féminin, O=Autre)
    gender = Column(String(10), nullable=False)
    
    # Poids en kilogrammes (optionnel, pour l'ajustement posologique)
    weight_kg = Column(Numeric(6, 2), nullable=True)
    
    # Taille en centimètres (optionnel)
    height_cm = Column(Numeric(6, 2), nullable=True)
    
    # Clairance rénale estimée en mL/min (optionnel, crucial pour l'alerte RENAL)
    # Permet de détecter les médicaments contre-indiqués en insuffisance rénale
    creatinine_clearance = Column(
        Numeric(6, 2), nullable=True
    )
    
    # Grossesse confirmée (déclenche les alertes CONTRA_INDICATION spécifiques)
    is_pregnant = Column(
        Boolean, default=False, nullable=True
    )
    
    # Semaine de grossesse si applicable (1–42 semaines)
    gestational_weeks = Column(
        SmallInteger, nullable=True
    )
    
    # Allaitement en cours (déclenche les alertes CONTRA_INDICATION)
    is_breastfeeding = Column(
        Boolean, default=False, nullable=True
    )
    
    # Liste des allergies documentées — scannée contre les DCI prescrites (règle ALLERGY)
    known_allergies = Column(
        ARRAY(Text), nullable=True
    )
    
    # Codes CIM-10 des pathologies chroniques (prédiabète, IRC, etc.)
    pathologies_cim10 = Column(
        ARRAY(Text), nullable=True
    )
    
    # Horodatage de création automatique côté serveur
    created_at = Column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )

    # Relation vers les prescriptions de ce patient
    prescriptions = relationship("Prescription", back_populates="patient")

    def __repr__(self):
        return f"<Patient id={self.id} birthdate={self.birthdate} gender={self.gender}>"
