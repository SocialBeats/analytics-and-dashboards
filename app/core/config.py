"""
Application configuration using Pydantic Settings
"""
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support"""

    # Application
    APP_NAME: str = Field(default="FastAPI MongoDB Template")
    APP_VERSION: str = Field(default="1.0.0")
    APP_DESCRIPTION: str = Field(default="A production-ready FastAPI + MongoDB template")
    ENVIRONMENT: str = Field(default="development")
    DEBUG: bool = Field(default=True)

    # Server
    HOST: str = Field(default="0.0.0.0")
    PORT: int = Field(default=3003)

    # Database
    MONGODB_URL: str = Field(default="mongodb://localhost:27017")
    MONGODB_DB_NAME: str = Field(default="fastapi_template")
    MONGODB_MAX_CONNECTIONS: int = Field(default=10)
    MONGODB_MIN_CONNECTIONS: int = Field(default=1)

    # CORS
    CORS_ORIGINS: List[str] = Field(default=["http://localhost:3000", "http://localhost:3003"])
    CORS_ALLOW_CREDENTIALS: bool = Field(default=True)
    CORS_ALLOW_METHODS: List[str] = Field(default=["*"])
    CORS_ALLOW_HEADERS: List[str] = Field(default=["*"])

    # Logging
    LOG_LEVEL: str = Field(default="INFO")
    LOG_FORMAT: str = Field(default="json")

    # Security & JWT Authentication
    # JWT_SECRET: Clave secreta para firmar/verificar tokens JWT
    #             DEBE ser la misma en todos los servicios que comparten autenticación
    #             El algoritmo se infiere automáticamente del header del token
    JWT_SECRET: str = Field(default="your-secret-key-here-change-in-production")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    @property
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.ENVIRONMENT.lower() == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment"""
        return self.ENVIRONMENT.lower() == "development"


# Global settings instance
settings = Settings()
