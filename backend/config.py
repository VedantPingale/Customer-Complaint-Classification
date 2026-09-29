"""Application configuration loaded from environment variables."""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Base configuration."""

    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-jwt-secret-change-in-production")
    JWT_EXPIRATION_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", "8"))

    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///complaints.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    MODEL_PATH = os.getenv("MODEL_PATH", "ml/models/classifier.joblib")
    VECTORIZER_PATH = os.getenv("VECTORIZER_PATH", "ml/models/vectorizer.joblib")
    CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.60"))
    MODEL_TYPE = os.getenv("MODEL_TYPE", "tfidf_lr")

    CFPB_DATA_PATH = os.getenv("CFPB_DATA_PATH", "ml/data/cfpb_complaints.csv")
    CFPB_SAMPLE_SIZE = int(os.getenv("CFPB_SAMPLE_SIZE", "50000"))

    PRIORITY_RULES_PATH = os.getenv("PRIORITY_RULES_PATH", "config/priority_rules.json")
    CATEGORIES_PATH = os.getenv("CATEGORIES_PATH", "config/categories.json")

    DEMO_ADMIN_PASSWORD = os.getenv("DEMO_ADMIN_PASSWORD", "admin123dev")
    DEMO_MANAGER_PASSWORD = os.getenv("DEMO_MANAGER_PASSWORD", "manager123dev")
    DEMO_AGENT_PASSWORD = os.getenv("DEMO_AGENT_PASSWORD", "agent123dev")


class DevelopmentConfig(Config):
    """Development configuration."""

    DEBUG = True


class ProductionConfig(Config):
    """Production configuration."""

    DEBUG = False


class TestingConfig(Config):
    """Testing configuration."""

    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"


config_map = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}


def get_config():
    """Get the configuration object based on the FLASK_ENV variable."""
    env = os.getenv("FLASK_ENV", "development")
    return config_map.get(env, DevelopmentConfig)
