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
    )
    
    status = Column(
        String(20), default="draft", nullable=False
    )
    
    hook_event = Column(
        String(50), default="order-sign", nullable=True
    )
    
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
    )
    
    dose_mg = Column(Numeric(12, 4), nullable=False)
    
    dose_unit_raw = Column(
        String(20), nullable=True
    )
    
    frequency = Column(String(100), nullable=True)
    
    route = Column(String(50), nullable=True)
    
    duration_days = Column(SmallInteger, nullable=True)

    prescription = relationship("Prescription", back_populates="lines")
    drug = relationship("Drug", foreign_keys=[drug_id])
    alerts = relationship(
        "CdsAlert", back_populates="prescription_line", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<PrescriptionLine id={self.id} dci={self.dci} dose_mg={self.dose_mg}>"
