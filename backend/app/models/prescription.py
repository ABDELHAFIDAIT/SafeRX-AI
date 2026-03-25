from sqlalchemy import (
    Column,
    Integer,
    String,
    SmallInteger,
    Numeric,
    ForeignKey,
    TIMESTAMP,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.app.db.base import Base


class Prescription(Base):
    """
    En-tête d'une prescription — relie un patient à un médecin et contient le statut CDS.
    Chaque prescription peut avoir plusieurs lignes (PrescriptionLine).
    """
    __tablename__ = "prescriptions"

    # Identifiant unique
    id = Column(Integer, primary_key=True, index=True)
    
    # Clé étrangère vers le patient
    patient_id = Column(
        Integer,
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Clé étrangère vers le médecin prescripteur
    doctor_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=False, index=True
    )
    
    # Identifiant FHIR du bundle CDS Hooks (optionnel, pour traçabilité)
    fhir_bundle_id = Column(
        UUID(as_uuid=True), unique=True, nullable=True
    )
    
    # Statut de la prescription (draft | alerts | safe)
    # draft = création en cours; alerts = au moins une alerte; safe = aucune alerte
    status = Column(
        String(20), default="draft", nullable=False
    )
    
    # Événement CDS Hooks déclencheur (ex: order-sign pour une signature électronique)
    hook_event = Column(
        String(50), default="order-sign", nullable=True
    )
    
    # Horodatage de création automatique côté serveur
    created_at = Column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )

    # Relations ORM
    patient = relationship("Patient", back_populates="prescriptions")
    doctor = relationship("User", foreign_keys=[doctor_id])
    lines = relationship(
        "PrescriptionLine", back_populates="prescription", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Prescription id={self.id} patient_id={self.patient_id} status={self.status}>"


class PrescriptionLine(Base):
    """
    Ligne de prescription — un médicament avec sa posologie complète.
    Chaque ligne peut avoir plusieurs alertes CDS (CdsAlert).
    """
    __tablename__ = "prescription_lines"

    # Identifiant unique
    id = Column(Integer, primary_key=True, index=True)
    
    # Clé étrangère vers la prescription parent
    prescription_id = Column(
        Integer,
        ForeignKey("prescriptions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Clé étrangère vers le médicament référentiel
    drug_id = Column(
        Integer, ForeignKey("drugs_ma.id", ondelete="RESTRICT"), nullable=False
    )
    
    # DCI telle que saisie par le médecin (peut contenir des variantes d'orthographe)
    dci = Column(
        String(255), nullable=False, index=True
    )
    
    # Dose normalisée en milligrammes
    dose_mg = Column(Numeric(12, 4), nullable=False)
    
    # Unité d'origine avant normalisation (ex: mg, µg, g, mL)
    dose_unit_raw = Column(
        String(20), nullable=True
    )
    
    # Fréquence de prise (ex: "2 fois par jour", "une fois à 8h")
    frequency = Column(String(100), nullable=True)
    
    # Voie d'administration (ex: "per os", "IV", "IM", "cutanée")
    route = Column(String(50), nullable=True)
    
    # Durée du traitement en jours (1–3650 jours = ~10 ans)
    duration_days = Column(SmallInteger, nullable=True)

    # Relations ORM
    prescription = relationship("Prescription", back_populates="lines")
    drug = relationship("Drug", foreign_keys=[drug_id])
    alerts = relationship(
        "CdsAlert", back_populates="prescription_line", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<PrescriptionLine id={self.id} dci={self.dci} dose_mg={self.dose_mg}>"
