from backend.app.core.config import settings
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Moteur SQLAlchemy — connecté à la base PostgreSQL via l'URL configurée
engine = create_engine(settings.DATABASE_URL)

# Factory de sessions — crée des sessions DB avec autoflush/autocommit désactivés
SessionLocal = sessionmaker(
    autoflush=False, autocommit=False, bind=engine
)
