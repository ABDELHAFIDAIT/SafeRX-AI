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
    # En-tête d'une prescription — relie un patient à un médecin et contient le statut CDS
    __tablename__ = "prescriptions"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(
        Integer,
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    doctor_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=False, index=True
    )
    fhir_bundle_id = Column(
        UUID(as_uuid=True), unique=True, nullable=True
    )  # identifiant FHIR du bundle CDS Hooks
    status = Column(
        String(20), default="draft", nullable=False
    )  # draft | alerts | safe
    hook_event = Column(
        String(50), default="order-sign", nullable=True
    )  # événement CDS Hooks déclencheur
    created_at = Column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )

    patient = relationship("Patient", back_populates="prescriptions")
    doctor = relationship("User", foreign_keys=[doctor_id])
    lines = relationship(
        "PrescriptionLine", back_populates="prescription", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Prescription id={self.id} patient_id={self.patient_id} status={self.status}>"


class PrescriptionLine(Base):
    # Ligne de prescription — un médicament avec sa posologie complète
    __tablename__ = "prescription_lines"

    id = Column(Integer, primary_key=True, index=True)
    prescription_id = Column(
        Integer,
        ForeignKey("prescriptions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    drug_id = Column(
        Integer, ForeignKey("drugs_ma.id", ondelete="RESTRICT"), nullable=False
    )
    dci = Column(
        String(255), nullable=False, index=True
    )  # DCI telle que saisie par le médecin
    dose_mg = Column(Numeric(12, 4), nullable=False)  # dose normalisée en milligrammes
    dose_unit_raw = Column(
        String(20), nullable=True
    )  # unité d'origine avant normalisation
    frequency = Column(String(100), nullable=True)  # ex: "2 fois par jour"
    route = Column(String(50), nullable=True)  # voie d'administration
    duration_days = Column(SmallInteger, nullable=True)  # durée en jours (1–3650)

    prescription = relationship("Prescription", back_populates="lines")
    drug = relationship("Drug", foreign_keys=[drug_id])
    alerts = relationship(
        "CdsAlert", back_populates="prescription_line", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<PrescriptionLine id={self.id} dci={self.dci} dose_mg={self.dose_mg}>"
