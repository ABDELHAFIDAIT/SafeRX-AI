"""
SafeRx AI — Modèle audit_cds_hooks
════════════════════════════════════
Trace chaque décision du praticien face à une alerte CDS.
Exigence légale HDS — immuable (pas de UPDATE/DELETE).

Décisions possibles :
  ACCEPTED  — Le praticien prend note de l'alerte et adapte la prescription
  IGNORED   — Le praticien ignore l'alerte (justification recommandée)
  OVERRIDE  — Le praticien maintient la prescription malgré l'alerte (justification obligatoire)
"""
from __future__ import annotations

from sqlalchemy import (
    Column, Integer, String, Text,
    ForeignKey, DateTime, func
)

from backend.app.db.base import Base


class AuditCdsHook(Base):
    __tablename__ = "audit_cds_hooks"

    id              = Column(Integer, primary_key=True, index=True)

    # ── Liens ─────────────────────────────────────────────────────────────
    alert_id        = Column(
        Integer,
        ForeignKey("cds_alerts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    prescription_id = Column(
        Integer,
        ForeignKey("prescriptions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    doctor_id       = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # ── Décision ──────────────────────────────────────────────────────────
    # ACCEPTED | IGNORED | OVERRIDE
    decision        = Column(String(20), nullable=False)

    # Contexte de l'alerte au moment de la décision (snapshot)
    alert_type      = Column(String(50),  nullable=True)
    alert_severity  = Column(String(20),  nullable=True)
    alert_title     = Column(String(255), nullable=True)

    # Justification libre (obligatoire pour OVERRIDE, recommandée pour IGNORED)
    justification          = Column(Text,    nullable=True)

    # ── Validation sémantique (§3.3) ──────────────────────────────────────
    # True  = justification médicalement valide selon le LLM
    # False = bruit / justification insuffisante
    # None  = pas encore analysé ou non applicable
    justification_valid    = Column(String(10), nullable=True)   # "valid" | "noise" | None
    justification_feedback = Column(Text,       nullable=True)   # explication courte du LLM

    # ── Horodatage ────────────────────────────────────────────────────────
    created_at      = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self):
        return (
            f"<AuditCdsHook id={self.id} "
            f"decision={self.decision} "
            f"alert_id={self.alert_id}>"
        )