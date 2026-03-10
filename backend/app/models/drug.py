from sqlalchemy import Column, Integer, String, Float, Boolean,ForeignKey, Text
from sqlalchemy.orm import relationship
from backend.app.db.base import Base



class Drug(Base):
    __tablename__ = "drugs_ma"
    
    id = Column(Integer, primary_key=True, index=True)
    brand_name = Column(String, nullable=False, index=True)
    presentation = Column(String)
    dosage_raw = Column(String)
    dci = Column(Text)
    labo_name = Column(String)
    therapeutic_class = Column(String)
    status = Column(String)
    atc_code = Column(String,  index=True)
    price_ppv = Column(Float)
    price_hospital = Column(Float)
    toxicity_class = Column(String)
    product_type = Column(String)
    indications = Column(Text)
    is_psychoactive = Column(Boolean, default=False, nullable=False)
    contraindications = Column(Text)
    min_age = Column(String)
    source_url = Column(String)
    
    dci_components    = relationship("DciComponent", back_populates="drug", cascade="all, delete-orphan")
    



class DciComponent(Base):
    __tablename__ = "dci_components"

    id = Column(Integer, primary_key=True, autoincrement=True)
    drug_id = Column(Integer, ForeignKey("drugs_ma.id", ondelete="CASCADE"), nullable=False, index=True)
    dci = Column(Text, nullable=False, index=True)
    position = Column(Integer, nullable=False)

    drug     = relationship("Drug", back_populates="dci_components")