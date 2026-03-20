from __future__ import annotations
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, field_validator

# Ensemble des décisions valides — utilisé pour la validation côté schema
VALID_DECISIONS = {"ACCEPTED", "IGNORED", "OVERRIDE"}


class AuditCreate(BaseModel):
    # Payload envoyé par le frontend pour enregistrer la décision du praticien sur une alerte
    alert_id: int
    prescription_id: int
    decision: Literal["ACCEPTED", "IGNORED", "OVERRIDE"]
    justification: str | None = None

    @field_validator("justification")
    @classmethod
    def justification_required_for_override(cls, v, info):
        # Bloque un OVERRIDE sans justification — contrainte métier obligatoire
        decision = info.data.get("decision")
        if decision == "OVERRIDE" and not (v and v.strip()):
            raise ValueError("Une justification est obligatoire pour un OVERRIDE.")
        return v


class AuditOut(BaseModel):
    # Schéma de réponse complet incluant le résultat de la validation sémantique LLM
    id: int
    alert_id: int | None
    prescription_id: int | None
    doctor_id: int | None
    decision: str
    alert_type: str | None
    alert_severity: str | None
    alert_title: str | None
    justification: str | None
    justification_valid: str | None = (
        None  # "valid" | "noise" | None selon l'analyse LLM
    )
    justification_feedback: str | None = None  # retour textuel court du LLM
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditBulkCreate(BaseModel):
    # Permet de logger toutes les décisions d'une prescription en une seule requête
    prescription_id: int
    decisions: list[AuditCreate]
