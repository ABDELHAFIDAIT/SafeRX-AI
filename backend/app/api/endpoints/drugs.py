from __future__ import annotations
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.api.deps import get_current_user, get_db
from backend.app.models.drug import Drug, DciComponent
from backend.app.models.user import User
from pydantic import BaseModel


router = APIRouter()


class DrugSearchResult(BaseModel):
    """Schéma pour afficher un résultat de recherche de médicament."""
    # Résultat enrichi de recherche médicament
    id: int
    brand_name: str
    presentation: str | None = None
    dosage_raw: str | None = None
    dci: str | None = None
    labo_name: str | None = None
    atc_code: str | None = None
    price_ppv: float | None = None
    price_hospital: float | None = None
    product_type: str | None = None
    indications: str | None = None
    min_age: str | None = None
    is_psychoactive: bool = False

    model_config = {"from_attributes": True}


class DciComponentOut(BaseModel):
    """Schéma pour un composant actif (DCI) au sein d'un médicament multi-actif."""
    id: int
    dci: str
    position: int
    
    model_config = {"from_attributes": True}


class DrugDetailOut(BaseModel):
    """Schéma complet pour afficher les détails d'un médicament avec tous ses composants."""
    # Réponse complète pour la fiche médicament détaillée
    id: int
    brand_name: str
    presentation: str | None = None
    dci: str | None = None
    is_psychoactive: bool
    min_age: str | None = None
    labo_name: str | None = None
    therapeutic_class: str | None = None
    indications: str | None = None
    contraindications: str | None = None
    price_ppv: float | None = None
    price_hospital: float | None = None
    dci_components: list[DciComponentOut] = []
    
    model_config = {"from_attributes": True}


@router.get("/search", response_model=list[DrugSearchResult])
def search_drugs(
    q: str = Query(..., min_length=2, description="Nom de marque ou DCI"),
    limit: int = Query(default=8, le=20),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    pattern = f"%{q.strip()}%"  # pattern ILIKE pour la recherche insensible à la casse

    drugs = (
        db.query(Drug)
        .filter(
            Drug.brand_name.ilike(pattern)
            | Drug.dci.ilike(pattern)  # recherche sur nom de marque ET sur DCI
        )
        .order_by(
            Drug.brand_name.ilike(
                f"{q.strip()}%"
            ).desc(),  # résultats commençant par la requête en premier
            Drug.brand_name,
        )
        .limit(limit)
        .all()
    )

    results = []
    for drug in drugs:
        # Récupère uniquement la DCI primaire (position=1) pour l'affichage
        primary = (
            db.query(DciComponent.dci)
            .filter(DciComponent.drug_id == drug.id, DciComponent.position == 1)
            .scalar()
        )
        results.append(
            DrugSearchResult(
                id=drug.id,
                brand_name=drug.brand_name,
                presentation=drug.presentation,
                dosage_raw=drug.dosage_raw,
                dci=primary or drug.dci,  # fallback sur le champ dci brut si pas de composant
                labo_name=drug.labo_name,
                atc_code=drug.atc_code,
                price_ppv=float(drug.price_ppv) if drug.price_ppv else None,
                price_hospital=float(drug.price_hospital) if drug.price_hospital else None,
                product_type=drug.product_type,
                indications=drug.indications,
                min_age=drug.min_age,
                is_psychoactive=drug.is_psychoactive or False,
            )
        )

    return results


@router.get("/{drug_id}", response_model=DrugDetailOut)
def get_drug_detail(
    drug_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    drug = db.query(Drug).filter(Drug.id == drug_id).first()
    
    if not drug:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Médicament {drug_id} introuvable."
        )
    
    # Charger les composants DCI
    dci_components = (
        db.query(DciComponent)
        .filter(DciComponent.drug_id == drug_id)
        .order_by(DciComponent.position)
        .all()
    )
    
    return DrugDetailOut(
        id=drug.id,
        brand_name=drug.brand_name,
        presentation=drug.presentation,
        dci=drug.dci,
        is_psychoactive=drug.is_psychoactive,
        min_age=drug.min_age,
        labo_name=drug.labo_name,
        therapeutic_class=drug.therapeutic_class,
        indications=drug.indications,
        contraindications=drug.contraindications,
        price_ppv=float(drug.price_ppv) if drug.price_ppv else None,
        price_hospital=float(drug.price_hospital) if drug.price_hospital else None,
        dci_components=dci_components,
    )
