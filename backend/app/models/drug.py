from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from backend.app.db.base import Base


class Drug(Base):
    # Médicament importé depuis medicament.ma — référentiel pharmaceutique marocain
    __tablename__ = "drugs_ma"

    id                 = Column(Integer, primary_key=True, index=True)
    brand_name         = Column(String,  nullable=False, index=True)
    presentation       = Column(String)
    dosage_raw         = Column(String)              # dosage brut tel qu'extrait de la source
    dci                = Column(Text)                # DCI complète (peut contenir plusieurs molécules)
    labo_name          = Column(String)
    therapeutic_class  = Column(String)
    status             = Column(String)
    atc_code           = Column(String,  index=True)
    price_ppv          = Column(Float)               # prix public en MAD
    price_hospital     = Column(Float)
    toxicity_class     = Column(String)
    product_type       = Column(String)
    indications        = Column(Text)
    is_psychoactive    = Column(Boolean, default=False, nullable=False)  # flag pour la règle PSYCHOACTIVE
    contraindications  = Column(Text)                # texte libre des CI — scanné par le moteur CDS
    min_age            = Column(String)              # âge minimal (ex : "6 mois", "12 ans")
    source_url         = Column(String)

    dci_components = relationship("DciComponent", back_populates="drug", cascade="all, delete-orphan")


class DciComponent(Base):
    # Décomposition d'un médicament en ses molécules actives (DCI individuelles)
    __tablename__ = "dci_components"

    id      = Column(Integer, primary_key=True, autoincrement=True)
    drug_id = Column(Integer, ForeignKey("drugs_ma.id", ondelete="CASCADE"), nullable=False, index=True)
    dci     = Column(Text,    nullable=False, index=True)  # DCI normalisée — utilisée par le moteur CDS
    position = Column(Integer, nullable=False)             # 1 = DCI primaire, >1 = DCI secondaire

    drug = relationship("Drug", back_populates="dci_components")