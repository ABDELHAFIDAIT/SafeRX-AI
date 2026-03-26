from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    
    # Métadonnées de l'application
    PROJECT_NAME: str
    API_STR: str
    VERSION: str

    # Paramètres de connexion PostgreSQL
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int
    DATABASE_URL: str

    # Configuration JWT pour l'authentification
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int

    # Admin initial (crée automatiquement au premier démarrage)
    ADMIN_EMAIL: str
    ADMIN_PASSWORD: str

    # Serveur SMTP pour l'envoi des identifiants
    SMTP_HOST: str
    SMTP_PORT: int
    SMTP_TLS: bool
    SMTP_USER: str
    SMTP_PASSWORD: str
    SMTP_FROM_EMAIL: str

    # Configuration LLM (Ollama ou Gemini pour l'enrichissement RAG)
    LLM_PROVIDER: str
    LLM_MODEL: str
    OLLAMA_BASE_URL: str
    GEMINI_API_KEY: str
    GEMINI_MODEL: str
    EMBEDDING_MODEL: str

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",
    )


# Instance globale des paramètres
settings = Settings()
