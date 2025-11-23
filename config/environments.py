"""
Environment-specific configuration management.
Supports multiple environments: development, staging, production
"""
import os
from typing import Dict, Any
from config.settings import Config


class DevelopmentConfig(Config):
    """Development environment configuration."""
    ENVIRONMENT = 'development'
    FLASK_ENV = 'development'
    LOG_LEVEL = 'DEBUG'
    DEBUG = True
    
    # Development database (SQLite)
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///data/social_media.db')
    
    # Development Redis (local)
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    
    # Development settings
    TESTING = False
    PROPAGATE_EXCEPTIONS = True


class StagingConfig(Config):
    """Staging environment configuration."""
    ENVIRONMENT = 'staging'
    FLASK_ENV = 'production'
    LOG_LEVEL = 'INFO'
    DEBUG = False
    
    # Staging database (PostgreSQL)
    DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://user:pass@staging-db:5432/social_media')
    
    # Staging Redis
    REDIS_URL = os.getenv('REDIS_URL', 'redis://staging-redis:6379/0')
    
    # Staging settings
    TESTING = False
    PROPAGATE_EXCEPTIONS = False


class ProductionConfig(Config):
    """Production environment configuration."""
    ENVIRONMENT = 'production'
    FLASK_ENV = 'production'
    LOG_LEVEL = 'WARNING'
    DEBUG = False
    
    # Production database (PostgreSQL with connection pooling)
    DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://user:pass@prod-db:5432/social_media')
    
    # Production Redis (cluster)
    REDIS_URL = os.getenv('REDIS_URL', 'redis://prod-redis:6379/0')
    
    # Production settings
    TESTING = False
    PROPAGATE_EXCEPTIONS = False
    
    # Security settings
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'


class TestingConfig(Config):
    """Testing environment configuration."""
    ENVIRONMENT = 'testing'
    FLASK_ENV = 'testing'
    LOG_LEVEL = 'DEBUG'
    DEBUG = True
    TESTING = True
    
    # Test database (in-memory SQLite)
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///:memory:')
    
    # Test Redis (mock or local)
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/1')
    
    # Testing settings
    PROPAGATE_EXCEPTIONS = True
    WTF_CSRF_ENABLED = False


# Configuration mapping
config_map: Dict[str, Any] = {
    'development': DevelopmentConfig,
    'staging': StagingConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
}


def get_config(environment: str = None) -> Config:
    """
    Get configuration for specified environment.
    
    Args:
        environment: Environment name (development, staging, production, testing)
                    If None, uses ENVIRONMENT environment variable or defaults to development
    
    Returns:
        Config instance for the specified environment
    """
    if environment is None:
        environment = os.getenv('ENVIRONMENT', 'development').lower()
    
    config_class = config_map.get(environment, DevelopmentConfig)
    return config_class()


# Default config instance
config = get_config()

