from __future__ import annotations
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


# ── Schémas Patient ───────────────────────────────────────────────────────────

class PatientBase(BaseModel):
    # Champs communs à la création et à la lecture d'un patient
    birthdate:            date
    gender:               str = Field(..., pattern="^(M|F|O)$")  # M=Masculin, F=Féminin, O=Autre
    weight_kg:            Optional[Decimal] = None
    height_cm:            Optional[Decimal] = None
    creatinine_clearance: Optional[Decimal] = None
    is_pregnant:          Optional[bool]    = False
    gestational_weeks:    Optional[int]     = None
    is_breastfeeding:     Optional[bool]    = False
    known_allergies:      Optional[List[str]] = None
    pathologies_cim10:    Optional[List[str]] = None

    @field_validator("gestational_weeks")
    @classmethod
    def check_gestational_weeks(cls, v, info):
        # Valide que la semaine de grossesse est dans la plage physiologique 1–42
        if v is not None and not (1 <= v <= 42):
            raise ValueError("gestational_weeks doit être entre 1 et 42")
        return v


class PatientCreate(PatientBase):
    # Ajoute l'identifiant FHIR optionnel lors de la création
    fhir_patient_id: Optional[uuid.UUID] = None


class PatientUpdate(BaseModel):
    # Mise à jour partielle — seuls les champs cliniques sont modifiables
    weight_kg:            Optional[Decimal] = None
    height_cm:            Optional[Decimal] = None
    creatinine_clearance: Optional[Decimal] = None
    is_pregnant:          Optional[bool]    = None
    gestational_weeks:    Optional[int]     = None
    is_breastfeeding:     Optional[bool]    = None
    known_allergies:      Optional[List[str]] = None
    pathologies_cim10:    Optional[List[str]] = None


class PatientOut(PatientBase):
    id:              int
    fhir_patient_id: Optional[uuid.UUID] = None
    created_at:      datetime

    model_config = {"from_attributes": True}


# ── Schémas Ligne de Prescription ────────────────────────────────────────────

class PrescriptionLineBase(BaseModel):
    drug_id:       int
    dci:           str = Field(..., min_length=1, max_length=255)
    dose_mg:       Decimal = Field(..., gt=0, description="Dose normalisée en mg")
    dose_unit_raw: Optional[str]  = None                              # unité saisie avant normalisation
    frequency:     Optional[str]  = None
    route:         Optional[str]  = None
    duration_days: Optional[int]  = Field(None, ge=1, le=3650)        # durée max 10 ans


class PrescriptionLineCreate(PrescriptionLineBase):
    pass


class CdsAlertOut(BaseModel):
    # Alerte CDS retournée dans la réponse — inclut les champs IA si disponibles
    id:              int
    alert_type:      str
    severity:        str
    title:           str
    detail:          Optional[str]     = None
    rag_explanation: Optional[str]     = None    # explication LLM générée par le RAG
    ai_ignore_proba: Optional[Decimal] = None    # proba d'être ignoré selon la LR
    created_at:      datetime

    model_config = {"from_attributes": True}


class PrescriptionLineOut(PrescriptionLineBase):
    id:              int
    prescription_id: int
    alerts:          List[CdsAlertOut] = []

    model_config = {"from_attributes": True}


# ── Schémas Prescription ──────────────────────────────────────────────────────

class PrescriptionCreate(BaseModel):
    patient_id:     int
    lines:          List[PrescriptionLineCreate] = Field(..., min_length=1)  # au moins 1 ligne requise
    fhir_bundle_id: Optional[uuid.UUID] = None
    hook_event:     Optional[str]       = "order-sign"


class PrescriptionOut(BaseModel):
    id:             int
    patient_id:     int
    doctor_id:      int
    fhir_bundle_id: Optional[uuid.UUID] = None
    status:         str                             # "draft" | "alerts" | "safe"
    hook_event:     Optional[str]       = None
    created_at:     datetime
    lines:          List[PrescriptionLineOut] = []

    model_config = {"from_attributes": True}


class CdsResponse(BaseModel):
    # Réponse structurée de l'analyse CDS Hooks — retournée au frontend après création
    prescription_id: int
    status:          str                  # "safe" si aucune alerte, "alerts" sinon
    alert_count:     int
    alerts:          List[CdsAlertOut]
    prescription:    PrescriptionOut