from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings) :
    # Informations générales de l'application
    PROJECT_NAME : str
    API_STR : str
    VERSION : str
    
    # Connexion PostgreSQL
    POSTGRES_USER : str
    POSTGRES_PASSWORD : str
    POSTGRES_DB : str
    POSTGRES_HOST : str
    POSTGRES_PORT : int
    
    DATABASE_URL : str  # URL SQLAlchemy construite depuis les variables ci-dessus
    
    # Authentification JWT
    JWT_SECRET_KEY : str
    JWT_ALGORITHM : str
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES : int
    
    # Compte administrateur initial créé au premier démarrage
    ADMIN_EMAIL : str
    ADMIN_PASSWORD : str
    
    # Configuration SMTP pour l'envoi des identifiants par email
    SMTP_HOST : str
    SMTP_PORT : int
    SMTP_TLS : bool
    SMTP_USER : str
    SMTP_PASSWORD : str
    SMTP_FROM_EMAIL : str
    
    # Configuration LLM
    LLM_PROVIDER : str
    LLM_MODEL : str
    OLLAMA_BASE_URL : str
    GEMINI_API_KEY : str
    GEMINI_MODEL : str
    EMBEDDING_MODEL : str
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore"  # ignore les variables .env non déclarées ici
    )

settings = Settings()