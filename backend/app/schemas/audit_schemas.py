"""
SafeRx AI — Schemas Pydantic : Audit trail
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, field_validator


VALID_DECISIONS = {"ACCEPTED", "IGNORED", "OVERRIDE"}


class AuditCreate(BaseModel):
    """Payload envoyé par le frontend pour logger une décision."""
    alert_id:        int
    prescription_id: int
    decision:        Literal["ACCEPTED", "IGNORED", "OVERRIDE"]
    justification:   str | None = None

    @field_validator("justification")
    @classmethod
    def justification_required_for_override(cls, v, info):
        decision = info.data.get("decision")
        if decision == "OVERRIDE" and not (v and v.strip()):
            raise ValueError("Une justification est obligatoire pour un OVERRIDE.")
        return v


class AuditOut(BaseModel):
    id:                     int
    alert_id:               int | None
    prescription_id:        int | None
    doctor_id:              int | None
    decision:               str
    alert_type:             str | None
    alert_severity:         str | None
    alert_title:            str | None
    justification:          str | None
    # ── §3.3 Validation sémantique ──────────────────────────────
    justification_valid:    str | None = None   # "valid" | "noise" | None
    justification_feedback: str | None = None   # feedback LLM
    # ────────────────────────────────────────────────────────────
    created_at:             datetime

    model_config = {"from_attributes": True}


class AuditBulkCreate(BaseModel):
    """Permet de logger toutes les décisions d'une prescription en une seule requête."""
    prescription_id: int
    decisions: list[AuditCreate]