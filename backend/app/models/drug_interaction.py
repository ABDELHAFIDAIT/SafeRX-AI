from __future__ import annotations
from sqlalchemy import Column, Integer, String, Text, DateTime, func, UniqueConstraint
from backend.app.db.base import Base


class DrugInteraction(Base):
    # Interactions médicamenteuses issues du Thésaurus ANSM (paires DCI normalisées)
    __tablename__ = "drug_interactions"

    id             = Column(Integer,      primary_key=True, index=True)
    dci_a          = Column(String(255),  nullable=False, index=True)   # première DCI de la paire
    dci_b          = Column(String(255),  nullable=False, index=True)   # seconde DCI de la paire
    level_fr       = Column(String(50),   nullable=False)               # libellé ANSM (ex: "Contre-indication")
    severity       = Column(String(20),   nullable=False)               # MAJOR | MODERATE | MINOR
    mechanism      = Column(Text)                                        # mécanisme pharmacologique
    recommendation = Column(Text)                                        # conduite à tenir ANSM
    source         = Column(String(50),   nullable=False, default="ANSM_2023")
    created_at     = Column(DateTime(timezone=True), server_default=func.now())

    # Contrainte d'unicité sur la paire (dci_a, dci_b) — les paires sont orientées dans la BDD
    __table_args__ = (
        UniqueConstraint("dci_a", "dci_b", name="uq_drug_interactions_pair"),
    )