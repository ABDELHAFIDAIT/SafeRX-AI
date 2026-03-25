from sqlalchemy.orm import Session
from backend.app.core.config import settings
from backend.app.core.security import get_password_hash
from backend.app.models.user import User, Role


def init_db(db: Session) -> None:
    """
    Initialise les données de base de la base de données.
    Crée le compte administrateur par défaut si aucun admin n'existe.
    Appelée au démarrage de l'application via le lifespan FastAPI.
    
    Args:
        db: Session SQLAlchemy pour la requête
    """
    # Cherche un compte admin existant
    user = (
        db.query(User)
        .filter(User.email == settings.ADMIN_EMAIL, User.role == Role.ADMIN)
        .first()
    )

    # Crée l'admin si absent
    if not user:
        new_user = User(
            first_name="Admin",
            last_name="User",
            email=settings.ADMIN_EMAIL,
            password=get_password_hash(settings.ADMIN_PASSWORD),
            role=Role.ADMIN,
            is_first_login=False,
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
