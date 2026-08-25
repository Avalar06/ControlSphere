from typing import List
from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = ConfigDict(case_sensitive=True, env_file=".env", extra="ignore")

    PROJECT_NAME: str = "ControlSphere"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    API_V1_STR: str = "/api/v1"

    # Security
    SECRET_KEY: str = "super_secret_dev_key_change_in_production_min_32_chars"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    ALGORITHM: str = "HS256"

    # Database
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres_secure_password"
    POSTGRES_DB: str = "controlsphere"
    DATABASE_URL: str | None = None

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://localhost:8000",
    ]

    # First Superuser / Initial Seed
    FIRST_SUPERUSER_EMAIL: str = "admin@apexfinancial.com"
    FIRST_SUPERUSER_PASSWORD: str = "AdminPassword123!"

    # Phase 3 Evidence Storage Configuration
    EVIDENCE_STORAGE_ROOT: str = "storage/evidence"
    MAX_EVIDENCE_FILE_SIZE_MB: int = 25
    ALLOWED_EVIDENCE_EXTENSIONS: List[str] = [
        ".pdf",
        ".docx",
        ".xlsx",
        ".csv",
        ".txt",
        ".png",
        ".jpg",
        ".jpeg",
    ]

    @property
    def sync_database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"


settings = Settings()