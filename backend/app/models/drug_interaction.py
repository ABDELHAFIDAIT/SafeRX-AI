from __future__ import annotations
from sqlalchemy import Column, Integer, String, Text, DateTime, func, UniqueConstraint
from backend.app.db.base import Base


class DrugInteraction(Base):
    __tablename__ = "drug_interactions"

    id = Column(Integer, primary_key=True, index=True)
    
    dci_a = Column(String(255), nullable=False, index=True)
    
    dci_b = Column(String(255), nullable=False, index=True)
    
    level_fr = Column(
        String(50), nullable=False
    )
    
    severity = Column(String(20), nullable=False)
    
    mechanism = Column(Text)
    
    recommendation = Column(Text)
    
    source = Column(String(50), nullable=False, default="ANSM_2023")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("dci_a", "dci_b", name="uq_drug_interactions_pair"),
    )
