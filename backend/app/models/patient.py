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
    # Dossier patient — contient les données cliniques utilisées par le moteur CDS
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    fhir_patient_id = Column(
        UUID(as_uuid=True), unique=True, nullable=True
    )  # identifiant FHIR externe
    birthdate = Column(Date, nullable=False)
    gender = Column(String(10), nullable=False)  # M | F | O
    weight_kg = Column(Numeric(6, 2), nullable=True)
    height_cm = Column(Numeric(6, 2), nullable=True)
    creatinine_clearance = Column(
        Numeric(6, 2), nullable=True
    )  # utile pour les ajustements posologiques
    is_pregnant = Column(
        Boolean, default=False, nullable=True
    )  # déclenche la règle CONTRA_INDICATION grossesse
    gestational_weeks = Column(
        SmallInteger, nullable=True
    )  # semaine de grossesse (1–42)
    is_breastfeeding = Column(
        Boolean, default=False, nullable=True
    )  # déclenche la règle CONTRA_INDICATION allaitement
    known_allergies = Column(
        ARRAY(Text), nullable=True
    )  # liste des allergènes — utilisée par la règle ALLERGY
    pathologies_cim10 = Column(
        ARRAY(Text), nullable=True
    )  # codes CIM-10 des pathologies chroniques
    created_at = Column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )

    prescriptions = relationship("Prescription", back_populates="patient")

    def __repr__(self):
        return f"<Patient id={self.id} birthdate={self.birthdate} gender={self.gender}>"
