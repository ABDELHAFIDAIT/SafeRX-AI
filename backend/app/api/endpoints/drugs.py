from __future__ import annotations
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from backend.app.api.deps import get_current_user, get_db
from backend.app.models.drug import Drug, DciComponent
from backend.app.models.user import User
from pydantic import BaseModel

router = APIRouter()


class DrugSearchResult(BaseModel):
    # Résultat allégé de recherche médicament — évite de sérialiser toute la table
    id:              int
    brand_name:      str
    presentation:    str | None = None
    dci:             str | None = None
    is_psychoactive: bool = False

    model_config = {"from_attributes": True}


@router.get("/search", response_model=list[DrugSearchResult])
def search_drugs(
    q:     str = Query(..., min_length=2, description="Nom de marque ou DCI"),
    limit: int = Query(default=8, le=20),
    db:    Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    pattern = f"%{q.strip()}%"  # pattern ILIKE pour la recherche insensible à la casse

    drugs = (
        db.query(Drug)
        .filter(
            Drug.brand_name.ilike(pattern) |
            Drug.dci.ilike(pattern)  # recherche sur nom de marque ET sur DCI
        )
        .order_by(
            Drug.brand_name.ilike(f"{q.strip()}%").desc(),  # résultats commençant par la requête en premier
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
        results.append(DrugSearchResult(
            id=drug.id,
            brand_name=drug.brand_name,
            presentation=drug.presentation,
            dci=primary or drug.dci,          # fallback sur le champ dci brut si pas de composant
            is_psychoactive=drug.is_psychoactive or False,
        ))

    return results