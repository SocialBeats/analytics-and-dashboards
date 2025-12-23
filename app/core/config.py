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

    # Security & JWT Authentication (DEPRECATED)
    # JWT_SECRET: Ya NO se requiere en este microservicio.
    #             La autenticación se realiza en el API Gateway, que añade headers
    #             con la información del usuario. Este microservicio confía en esos headers.
    #             Mantenemos esta variable solo por compatibilidad, pero no se usa.
    JWT_SECRET: str = Field(default="")

    # Rate Limiting
    REDIS_URL: str = Field(default="redis://localhost:6379")

    # File Storage
    TEMP_AUDIO_DIR: str = Field(default="temp_audio")
    MAX_UPLOAD_SIZE: int = Field(default=100 * 1024 * 1024)  # 100MB

    # Microservices URLs
    BEATS_SERVICE_URL: str = Field(
        default="http://localhost:3005"
    )  # URL del microservicio de beats

    # Kafka Configuration
    KAFKA_BROKER: str = Field(default="localhost:9092")
    ENABLE_KAFKA: bool = Field(default=True)
    KAFKA_CONNECTION_MAX_RETRIES: int = Field(default=10)
    KAFKA_CONNECTION_RETRY_DELAY: int = Field(default=3000)  # milliseconds
    KAFKA_COOLDOWN: int = Field(default=30000)  # milliseconds
    # Kafka consumer tuning (milliseconds)
    KAFKA_SESSION_TIMEOUT_MS: int = Field(default=30000)
    KAFKA_HEARTBEAT_INTERVAL_MS: int = Field(default=10000)
    KAFKA_MAX_POLL_INTERVAL_MS: int = Field(default=300000)

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True, extra="ignore"
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
