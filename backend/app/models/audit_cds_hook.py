from __future__ import annotations
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, func
from backend.app.db.base import Base


class AuditCdsHook(Base):
    """
    Table immuable — retrace chaque décision du praticien face à une alerte CDS.
    Permet de construire un historique d'audit et d'entraîner le modèle LR sur les décisions.
    """
    __tablename__ = "audit_cds_hooks"

    # Identifiant unique
    id = Column(Integer, primary_key=True, index=True)

    # Clés étrangères avec ondelete SET NULL pour conserver l'audit même après suppression
    # Référence à l'alerte CDS associée
    alert_id = Column(
        Integer,
        ForeignKey("cds_alerts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    
    # Référence à la prescription concernée
    prescription_id = Column(
        Integer,
        ForeignKey("prescriptions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    
    # Référence au médecin auteur de la décision
    doctor_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Décision du médecin : ACCEPTED | IGNORED | OVERRIDE
    # ACCEPTED = l'alerte est valide; IGNORED = ignoré délibérément; OVERRIDE = l'alerte est fausse
    decision = Column(String(20), nullable=False)

    # Snapshot du contexte de l'alerte au moment de la décision (immuable pour l'historique)
    alert_type = Column(String(50), nullable=True)
    alert_severity = Column(String(20), nullable=True)
    alert_title = Column(String(255), nullable=True)

    # Justification libre — obligatoire pour OVERRIDE, recommandée pour IGNORED
    # Peut être validée sémantiquement par un modèle LLM
    justification = Column(Text, nullable=True)

    # Résultat de validation sémantique LLM du OVERRIDE justification
    # "valid" = justification cohérente; "noise" = justification non pertinente
    justification_valid = Column(String(10), nullable=True)
    
    # Retour textuel court du LLM sur la justification (texte libre)
    justification_feedback = Column(Text, nullable=True)

    # Horodatage automatique côté serveur SQL
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self):
        return (
            f"<AuditCdsHook id={self.id} "
            f"decision={self.decision} "
            f"alert_id={self.alert_id}>"
        )
