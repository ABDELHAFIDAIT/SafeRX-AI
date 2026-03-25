from sqlalchemy import Column, Integer, String, Text, Numeric, ForeignKey, TIMESTAMP
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.app.db.base import Base


class CdsAlert(Base):
    """
    Alerte clinique générée par le moteur CDS Rule Engine.
    Chaque alerte est rattachée à une ligne de prescription et peut être enrichie par RAG/LLM.
    """
    __tablename__ = "cds_alerts"

    # Identifiant unique
    id = Column(Integer, primary_key=True, index=True)
    
    # Clé étrangère vers la ligne de prescription concernée
    prescription_line_id = Column(
        Integer,
        ForeignKey("prescription_lines.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Type d'alerte (INTERACTION | ALLERGY | CONTRA_INDICATION | POSOLOGY | REDUNDANT_DCI | RENAL)
    alert_type = Column(
        String(50), nullable=False
    )
    
    # Sévérité de l'alerte (MAJOR | MODERATE | MINOR)
    severity = Column(String(20), nullable=False)
    
    # Titre court de l'alerte (ex: "Interaction médicamenteuse")
    title = Column(String(255), nullable=False)
    
    # Description clinique détaillée de l'alerte
    detail = Column(Text, nullable=True)
    
    # Explication générée par le RAG/LLM (optionnel et best-effort)
    rag_explanation = Column(Text, nullable=True)
    
    # Probabilité d'être ignorée par le médecin (0.0–1.0), estimée par Logistic Regression
    ai_ignore_proba = Column(
        Numeric(4, 3), nullable=True
    )
    
    # Horodatage de création automatique côté serveur
    created_at = Column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )

    # Relation vers la ligne de prescription parent
    prescription_line = relationship("PrescriptionLine", back_populates="alerts")

    def __repr__(self):
        return (
            f"<CdsAlert id={self.id} type={self.alert_type} "
            f"severity={self.severity} title={self.title[:40]}>"
        )
