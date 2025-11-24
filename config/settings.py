"""
Configuration management for the application.
Loads settings from environment variables with validation.
"""
import os
from typing import Optional
from dotenv import load_dotenv
from urllib.parse import urlparse

# Load environment variables from .env file
load_dotenv()


class Config:
    """Base configuration class."""

    # Application
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    FLASK_ENV: str = os.getenv("FLASK_ENV", "development")
    APP_PORT: int = int(os.getenv("APP_PORT", "5000"))
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # Database
    DATABASE_URL: str = (
        os.getenv("DATABASE_URL", "sqlite:///social_media.db")
        or "sqlite:///social_media.db"
    )

    @classmethod
    def get_db_path(cls) -> Optional[str]:
        """
        Extract SQLite database file path from DATABASE_URL.
        Returns None if not SQLite or if path cannot be extracted.
        """
        try:
            if not cls.DATABASE_URL or not cls.DATABASE_URL.strip():
                return None
            parsed = urlparse(cls.DATABASE_URL.strip())
            if parsed.scheme == "sqlite":
                # SQLite URLs can be: sqlite:///path or sqlite:///absolute/path
                path = parsed.path
                if not path:
                    return None
                if path.startswith("/"):
                    return path
                # Handle relative paths
                return path.lstrip("/")
            return None
        except Exception:
            return None

    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))

    # Security
    SECRET_KEY: Optional[str] = os.getenv("SECRET_KEY")
    JWT_SECRET_KEY: Optional[str] = os.getenv("JWT_SECRET_KEY")

    # Monitoring
    SENTRY_DSN: Optional[str] = os.getenv("SENTRY_DSN")

    # Celery
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", REDIS_URL)
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", REDIS_URL)

    # API Keys (optional)
    X_API_KEY: Optional[str] = os.getenv("X_API_KEY")
    INSTAGRAM_API_KEY: Optional[str] = os.getenv("INSTAGRAM_API_KEY")
    FACEBOOK_API_KEY: Optional[str] = os.getenv("FACEBOOK_API_KEY")
    YOUTUBE_API_KEY: Optional[str] = os.getenv("YOUTUBE_API_KEY")
    LINKEDIN_API_KEY: Optional[str] = os.getenv("LINKEDIN_API_KEY")

    # Email (optional)
    SMTP_HOST: Optional[str] = os.getenv("SMTP_HOST")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: Optional[str] = os.getenv("SMTP_USER")
    SMTP_PASSWORD: Optional[str] = os.getenv("SMTP_PASSWORD")
    SMTP_FROM_EMAIL: Optional[str] = os.getenv("SMTP_FROM_EMAIL")

    @classmethod
    def validate(cls) -> tuple[bool, list[str]]:
        """
        Validate configuration.
        Returns (is_valid, list_of_errors)
        """
        errors = []

        # Required in production
        if cls.ENVIRONMENT == "production":
            if not cls.SECRET_KEY:
                errors.append("SECRET_KEY is required in production")
            if not cls.JWT_SECRET_KEY:
                errors.append("JWT_SECRET_KEY is required in production")

        # Validate database URL format
        try:
            db_url = urlparse(cls.DATABASE_URL)
            if not db_url.scheme:
                errors.append(
                    "DATABASE_URL must have a valid scheme (sqlite://, postgresql://, etc.)"
                )
        except Exception as e:
            errors.append(f"Invalid DATABASE_URL format: {e}")

        # Validate Redis URL format
        try:
            redis_url = urlparse(cls.REDIS_URL)
            if redis_url.scheme not in ["redis", "rediss"]:
                errors.append("REDIS_URL must start with redis:// or rediss://")
        except Exception as e:
            errors.append(f"Invalid REDIS_URL format: {e}")

        # Validate port numbers
        if not (1 <= cls.APP_PORT <= 65535):
            errors.append(f"APP_PORT must be between 1 and 65535, got {cls.APP_PORT}")

        if not (1 <= cls.REDIS_PORT <= 65535):
            errors.append(
                f"REDIS_PORT must be between 1 and 65535, got {cls.REDIS_PORT}"
            )

        # Validate log level
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if cls.LOG_LEVEL.upper() not in valid_log_levels:
            errors.append(
                f"LOG_LEVEL must be one of {valid_log_levels}, got {cls.LOG_LEVEL}"
            )

        return len(errors) == 0, errors

    @classmethod
    def test_database_connection(cls) -> tuple[bool, Optional[str]]:
        """
        Test database connectivity.
        Returns (is_connected, error_message)
        """
        try:
            # Validate DATABASE_URL before using it
            if (
                not cls.DATABASE_URL
                or not isinstance(cls.DATABASE_URL, str)
                or not cls.DATABASE_URL.strip()
            ):
                return (
                    False,
                    f"Invalid DATABASE_URL: {cls.DATABASE_URL!r}. Must be a non-empty string.",
                )

            db_url = cls.DATABASE_URL.strip()

            # Validate URL format
            try:
                parsed = urlparse(db_url)
                if not parsed.scheme:
                    return (
                        False,
                        f"DATABASE_URL must have a valid scheme (sqlite://, postgresql://, etc.), got: {db_url!r}",
                    )
            except Exception as e:
                return False, f"Failed to parse DATABASE_URL: {e}"

            from sqlalchemy import create_engine, text

            engine = create_engine(db_url)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True, None
        except Exception as e:
            return False, f"Database connection failed: {str(e)}"

    @classmethod
    def test_redis_connection(cls) -> tuple[bool, Optional[str]]:
        """
        Test Redis connectivity.
        Returns (is_connected, error_message)
        """
        try:
            import redis

            r = redis.from_url(cls.REDIS_URL)
            r.ping()
            return True, None
        except Exception as e:
            return False, str(e)

    @classmethod
    def get_summary(cls) -> dict:
        """Get a summary of configuration (excluding secrets)."""
        return {
            "environment": cls.ENVIRONMENT,
            "flask_env": cls.FLASK_ENV,
            "app_port": cls.APP_PORT,
            "log_level": cls.LOG_LEVEL,
            "database_url": cls._mask_url(cls.DATABASE_URL),
            "redis_url": cls._mask_url(cls.REDIS_URL),
            "has_secret_key": bool(cls.SECRET_KEY),
            "has_jwt_secret": bool(cls.JWT_SECRET_KEY),
            "has_sentry": bool(cls.SENTRY_DSN),
        }

    @staticmethod
    def _mask_url(url: str) -> str:
        """Mask sensitive parts of URLs."""
        try:
            parsed = urlparse(url)
            if parsed.password:
                return url.replace(parsed.password, "***")
            return url
        except:
            return url


# Create config instance
config = Config()


def validate_config_on_startup():
    """Validate configuration when application starts."""
    is_valid, errors = config.validate()
    if not is_valid:
        error_msg = "Configuration validation failed:\n" + "\n".join(
            f"  - {e}" for e in errors
        )
        if config.ENVIRONMENT == "production":
            raise ValueError(error_msg)
        else:
            print(f"WARNING: {error_msg}")
    return is_valid
