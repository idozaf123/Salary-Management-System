"""
Configuration settings for Payroll Management System
"""

import os
from datetime import timedelta


class Config:
    """Base configuration"""

    # Application
    SECRET_KEY = os.environ.get("SECRET_KEY") or "dev-secret-key-change-in-production"
    DEBUG = False
    TESTING = False

    # Database
    DATABASE_PATH = os.environ.get("DATABASE_PATH") or "payroll.db"

    # Session
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)

    # API
    JSON_SORT_KEYS = False


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    # In production, always set SECRET_KEY via environment variable


class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DATABASE_PATH = ":memory:"  # Use in-memory database for tests


# Configuration dictionary
config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig
}
