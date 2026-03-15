from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.api.deps import get_current_user, get_db
from backend.app.models.user import User, Role
from backend.app.schemas.user import UserCreate, UserOut
from backend.app.services.user_service import create_user_with_password, update_password
from backend.app.services.email_service import send_credentials_email
import secrets
import string

router = APIRouter()


def _generate_password(length: int = 12) -> str:
    # Génère un mot de passe aléatoire alphanumérique + caractères spéciaux
    alphabet = string.ascii_letters + string.digits + "!@#$%"
    return "".join(secrets.choice(alphabet) for _ in range(length))


@router.post("/create", response_model=UserOut, status_code=status.HTTP_201_CREATED, summary="Créer un compte utilisateur (admin seulement)")
def create_account(payload: UserCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Seuls les admins peuvent créer des comptes
    if current_user.role != Role.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Réservé aux administrateurs.")

    # Empêche la création d'un compte avec un email déjà existant
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"L'adresse {payload.email} est déjà utilisée.")

    # Génère un mot de passe temporaire et crée le compte
    password = _generate_password()
    user = create_user_with_password(db=db, user_in=payload, password=password)

    # Envoie les identifiants par email — non bloquant si le serveur SMTP est indisponible
    try:
        send_credentials_email(to_email=user.email, first_name=user.first_name, role=payload.role, plain_password=password)
    except Exception:
        pass  # la création du compte réussit même si l'email échoue

    return user


@router.post("/change-password", summary="Changer son mot de passe (première connexion ou renouvellement)")
def change_password(payload: dict, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    new_password = payload.get("new_password", "")
    if len(new_password) < 8:
        # Validation minimale de longueur avant hashage
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Le mot de passe doit contenir au moins 8 caractères.")
    update_password(db=db, user=current_user, new_password=new_password)
    return {"message": "Mot de passe mis à jour avec succès."}


@router.get("/users", response_model=list[UserOut], summary="Lister tous les utilisateurs (admin seulement)")
def list_users(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Retourne tous les comptes triés par date de création décroissante
    if current_user.role != Role.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Réservé aux administrateurs.")
    return db.query(User).order_by(User.created_at.desc()).all()


# ─────────────────────────────────────────────────────────────────────────────
#  PATCH /account/users/{id}/toggle — Activer / désactiver un compte
# ─────────────────────────────────────────────────────────────────────────────

@router.patch(
    "/users/{user_id}/toggle",
    response_model=UserOut,
    summary="Activer ou désactiver un compte (admin seulement)",
)
def toggle_user_active(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != Role.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Réservé aux administrateurs.")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur introuvable.")
    if user.id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Impossible de désactiver son propre compte.")
    user.is_active = not user.is_active
    db.commit()
    db.refresh(user)
    return user


# ─────────────────────────────────────────────────────────────────────────────
#  DELETE /account/users/{id} — Supprimer un compte
# ─────────────────────────────────────────────────────────────────────────────

@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer un compte utilisateur (admin seulement)",
)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != Role.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Réservé aux administrateurs.")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur introuvable.")
    if user.id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Impossible de supprimer son propre compte.")
    db.delete(user)
    db.commit()


# ─────────────────────────────────────────────────────────────────────────────
#  POST /account/users/{id}/reset-password — Réinitialiser le MDP (admin)
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/users/{user_id}/reset-password",
    summary="Réinitialiser le mot de passe d'un utilisateur (admin seulement)",
)
def reset_user_password(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != Role.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Réservé aux administrateurs.")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur introuvable.")

    new_password = _generate_password()
    update_password(db=db, user=user, new_password=new_password)
    # Repasser is_first_login à True pour forcer le changement
    user.is_first_login = True
    db.commit()

    try:
        send_credentials_email(
            to_email=user.email,
            first_name=user.first_name,
            role=user.role,
            plain_password=new_password,
        )
    except Exception:
        pass

    return {"message": f"Mot de passe réinitialisé et envoyé à {user.email}."}


# ─────────────────────────────────────────────────────────────────────────────
#  GET /account/stats — Statistiques globales pour l'Overview admin
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/stats",
    summary="Statistiques globales du système (admin seulement)",
)
def get_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from backend.app.models.prescription import Prescription
    from backend.app.models.audit_cds_hook import AuditCdsHook
    from backend.app.models.cds_alert import CdsAlert
    from sqlalchemy import func
    from datetime import date, datetime, timezone

    if current_user.role != Role.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Réservé aux administrateurs.")

    today_start = datetime.combine(date.today(), datetime.min.time()).replace(tzinfo=timezone.utc)

    users       = db.query(User).all()
    total_presc = db.query(func.count(Prescription.id)).scalar() or 0
    presc_today = db.query(func.count(Prescription.id)).filter(
        Prescription.created_at >= today_start
    ).scalar() or 0

    total_audit = db.query(func.count(AuditCdsHook.id)).scalar() or 0
    overrides   = db.query(func.count(AuditCdsHook.id)).filter(
        AuditCdsHook.decision == "OVERRIDE"
    ).scalar() or 0
    accepted    = db.query(func.count(AuditCdsHook.id)).filter(
        AuditCdsHook.decision == "ACCEPTED"
    ).scalar() or 0

    # Top 5 types d'alertes les plus fréquentes
    top_alerts = (
        db.query(AuditCdsHook.alert_type, func.count(AuditCdsHook.id).label("cnt"))
        .filter(AuditCdsHook.alert_type.isnot(None))
        .group_by(AuditCdsHook.alert_type)
        .order_by(func.count(AuditCdsHook.id).desc())
        .limit(5)
        .all()
    )

    override_rate    = round((overrides / total_audit * 100), 1) if total_audit > 0 else 0
    compliance_rate  = round((accepted  / total_audit * 100), 1) if total_audit > 0 else 100

    return {
        "total_users":         len(users),
        "active_doctors":      sum(1 for u in users if u.role.value == "doctor"     and u.is_active),
        "active_pharmacists":  sum(1 for u in users if u.role.value == "pharmacist" and u.is_active),
        "total_prescriptions": total_presc,
        "prescriptions_today": presc_today,
        "total_audit_entries": total_audit,
        "override_rate":       override_rate,
        "compliance_rate":     compliance_rate,
        "top_alerts":          [{"type": r.alert_type, "count": r.cnt} for r in top_alerts],
    }
    
