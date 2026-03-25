from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from backend.app.db.base import Base


class Drug(Base):
    """
    Médicament importé depuis le référentiel marocain medicament.ma.
    Contient les données sur les spécialités pharmaceutiques, DCI, dosages et CI.
    """
    __tablename__ = "drugs_ma"

    # Identifiant unique
    id = Column(Integer, primary_key=True, index=True)
    
    # Nom de marque/spécialité du médicament
    brand_name = Column(String, nullable=False, index=True)
    
    # Présentation du médicament (ex: "comprimé", "sirop", "injection")
    presentation = Column(String)
    
    # Dosage brut tel qu'extrait de la source (peut contenir du texte libre)
    dosage_raw = Column(String)
    
    # DCI (Dénomination Commune Internationale) — peut contenir plusieurs molécules
    dci = Column(Text)
    
    # Laboratoire fabricant
    labo_name = Column(String)
    
    # Classe thérapeutique (ex: "AINS", "Antibiotique", "Inhibiteur de pompe")
    therapeutic_class = Column(String)
    
    # Statut du médicament (ex: "commercialisé", "retiré")
    status = Column(String)
    
    # Code ATC (Anatomical Therapeutic Chemical) — classement international
    atc_code = Column(String, index=True)
    
    # Prix public — PVP (Prix de Vente au Public) en MAD (Dirhams marocains)
    price_ppv = Column(Float)
    
    # Prix hospitalier en MAD
    price_hospital = Column(Float)
    
    # Classification de toxicité (ex: "T", "T+", "XN", etc.)
    toxicity_class = Column(String)
    
    # Type de produit (spécialité, générique, etc.)
    product_type = Column(String)
    
    # Indications thérapeutiques (texte libre — peut être scanné par le moteur CDS)
    indications = Column(Text)
    
    # Flag pour les substances psychoactives (déclenche alerte POSOLOGY MINOR)
    is_psychoactive = Column(
        Boolean, default=False, nullable=False
    )
    
    # Contre-indications (texte libre — scanné pour détection grossesse/allaitement)
    contraindications = Column(Text)
    
    # Âge minimal recommandé (ex: "6 mois", "12 ans")
    min_age = Column(String)
    
    # URL source de la fiche du médicament
    source_url = Column(String)

    # Relation vers les composants DCI de ce médicament
    dci_components = relationship(
        "DciComponent", back_populates="drug", cascade="all, delete-orphan"
    )


class DciComponent(Base):
    """
    Décomposition d'un médicament en ses molécules actives (DCI individuelles).
    Permet de gérer les polypharmacies et les redondances de DCI.
    """
    __tablename__ = "dci_components"

    # Identifiant unique
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Clé étrangère vers le médicament parent
    drug_id = Column(
        Integer,
        ForeignKey("drugs_ma.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # DCI normalisée — utilisée pour appariement avec le Thésaurus ANSM
    dci = Column(
        Text, nullable=False, index=True
    )
    
    # Position dans la liste des composants (1 = primaire, >1 = secondaire/excipient)
    # Permet de distinguer la molécule principale des excipients
    position = Column(Integer, nullable=False)

    # Relation vers le médicament parent
    drug = relationship("Drug", back_populates="dci_components")
