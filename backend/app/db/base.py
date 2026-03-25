from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """
    Classe de base pour tous les modèles SQLAlchemy de l'application.
    Permet à SQLAlchemy de mapper les classes Python aux tables PostgreSQL.
    """
    pass
