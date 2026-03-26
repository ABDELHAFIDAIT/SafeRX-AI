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
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    
    fhir_patient_id = Column(
        UUID(as_uuid=True), unique=True, nullable=True
    )
    
    birthdate = Column(Date, nullable=False)
    
    gender = Column(String(10), nullable=False)
    
    weight_kg = Column(Numeric(6, 2), nullable=True)
    
    height_cm = Column(Numeric(6, 2), nullable=True)
    
    creatinine_clearance = Column(
        Numeric(6, 2), nullable=True
    )
    
    is_pregnant = Column(
        Boolean, default=False, nullable=True
    )
    
    gestational_weeks = Column(
        SmallInteger, nullable=True
    )
    
    is_breastfeeding = Column(
        Boolean, default=False, nullable=True
    )
    
    known_allergies = Column(
        ARRAY(Text), nullable=True
    )
    
    pathologies_cim10 = Column(
        ARRAY(Text), nullable=True
    )
    
    created_at = Column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )

    prescriptions = relationship("Prescription", back_populates="patient")

    def __repr__(self):
        return f"<Patient id={self.id} birthdate={self.birthdate} gender={self.gender}>"
