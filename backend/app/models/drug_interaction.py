from __future__ import annotations
from sqlalchemy import Column, Integer, String, Text, DateTime, func, UniqueConstraint
from backend.app.db.base import Base


class DrugInteraction(Base):
    """
    Interaction médicamenteuse issue du Thésaurus ANSM (base de référence).
    Stocke les paires DCI avec leurs niveaux d'interaction et recommandations.
    """
    __tablename__ = "drug_interactions"

    # Identifiant unique
    id = Column(Integer, primary_key=True, index=True)
    
    # Première DCI de la paire (normalized en MAJUSCULES sans accents)
    dci_a = Column(String(255), nullable=False, index=True)
    
    # Seconde DCI de la paire (normalized en MAJUSCULES sans accents)
    dci_b = Column(String(255), nullable=False, index=True)
    
    # Libellé ANSM des niveaux d'interaction (ex: "Contre-indication", "Déconseillé", etc.)
    level_fr = Column(
        String(50), nullable=False
    )
    
    # Sévérité normalisée (MAJOR | MODERATE | MINOR)
    severity = Column(String(20), nullable=False)
    
    # Mécanisme pharmacologique de l'interaction
    mechanism = Column(Text)
    
    # Conduite à tenir — recommandation clinique officielle ANSM
    recommendation = Column(Text)
    
    # Source de la donnée (ex: "ANSM_2023")
    source = Column(String(50), nullable=False, default="ANSM_2023")
    
    # Horodatage de création automatique côté serveur
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Contrainte d'unicité sur la paire DCI — évite les doublons
    __table_args__ = (
        UniqueConstraint("dci_a", "dci_b", name="uq_drug_interactions_pair"),
    )
