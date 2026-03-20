from __future__ import annotations
import uuid
from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator

# ── Schémas Patient ───────────────────────────────────────────────────────────


class PatientBase(BaseModel):
    birthdate: date
    gender: str = Field(..., pattern="^(M|F|O)$")
    # float au lieu de Decimal — SQLAlchemy Column(Float) attend un float, pas un Decimal
    weight_kg: Optional[float] = None
    height_cm: Optional[float] = None
    creatinine_clearance: Optional[float] = None
    is_pregnant: Optional[bool] = False
    gestational_weeks: Optional[int] = None
    is_breastfeeding: Optional[bool] = False
    # default_factory=list et non None — évite d'insérer NULL dans les colonnes JSON
    known_allergies: Optional[List[str]] = Field(default_factory=list)
    pathologies_cim10: Optional[List[str]] = Field(default_factory=list)

    @field_validator("gestational_weeks")
    @classmethod
    def check_gestational_weeks(cls, v, info):
        if v is not None and not (1 <= v <= 42):
            raise ValueError("gestational_weeks doit être entre 1 et 42")
        return v


class PatientCreate(PatientBase):
    fhir_patient_id: Optional[uuid.UUID] = None


class PatientUpdate(BaseModel):
    weight_kg: Optional[float] = None
    height_cm: Optional[float] = None
    creatinine_clearance: Optional[float] = None
    is_pregnant: Optional[bool] = None
    gestational_weeks: Optional[int] = None
    is_breastfeeding: Optional[bool] = None
    known_allergies: Optional[List[str]] = None
    pathologies_cim10: Optional[List[str]] = None


class PatientOut(PatientBase):
    id: int
    fhir_patient_id: Optional[uuid.UUID] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Schémas Ligne de Prescription ────────────────────────────────────────────


class PrescriptionLineBase(BaseModel):
    drug_id: int
    dci: str = Field(..., min_length=1, max_length=255)
    dose_mg: float = Field(..., gt=0, description="Dose normalisée en mg")
    dose_unit_raw: Optional[str] = None
    frequency: Optional[str] = None
    route: Optional[str] = None
    duration_days: Optional[int] = Field(None, ge=1, le=3650)


class PrescriptionLineCreate(PrescriptionLineBase):
    pass


class CdsAlertOut(BaseModel):
    id: int
    alert_type: str
    severity: str
    title: str
    detail: Optional[str] = None
    rag_explanation: Optional[str] = None
    ai_ignore_proba: Optional[float] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class PrescriptionLineOut(PrescriptionLineBase):
    id: int
    prescription_id: int
    alerts: List[CdsAlertOut] = []

    model_config = {"from_attributes": True}


# ── Schémas Prescription ──────────────────────────────────────────────────────


class PrescriptionCreate(BaseModel):
    patient_id: int
    lines: List[PrescriptionLineCreate] = Field(..., min_length=1)
    fhir_bundle_id: Optional[uuid.UUID] = None
    hook_event: Optional[str] = "order-sign"


class PrescriptionOut(BaseModel):
    id: int
    patient_id: int
    doctor_id: int
    fhir_bundle_id: Optional[uuid.UUID] = None
    status: str
    hook_event: Optional[str] = None
    created_at: datetime
    lines: List[PrescriptionLineOut] = []

    model_config = {"from_attributes": True}


class CdsResponse(BaseModel):
    prescription_id: int
    status: str
    alert_count: int
    alerts: List[CdsAlertOut]
    prescription: PrescriptionOut
