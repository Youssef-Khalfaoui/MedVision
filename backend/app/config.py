"""MedVision — Application Configuration.

Toutes les variables d'environnement sont lues via pydantic-settings.
Le défaut fonctionnel permet de lancer l'app sans .env pour le développement.

V2: Ajouté guarde-fou JWT : impossible de lancer en production avec la clé par défaut.
"""
import os
import warnings
from pydantic_settings import BaseSettings
from functools import lru_cache


_DEFAULT_JWT_SECRET = "change-me-in-production-use-a-real-secret"


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://medvision:medvision_dev@localhost:5432/medvision"
    db_host: str = "localhost"
    db_port: int = 5433
    db_name: str = "medvision"
    db_user: str = "medvision"
    db_password: str = "medvisionpass"

    redis_host: str = "localhost"
    redis_port: int = 6379

    ai_api_url: str = "http://localhost:8002/analyze"

    # Production : mettre JWT_SECRET dans .env / variables d'environnement.
    # Si non défini, un avertissement est émis au démarrage.
    jwt_secret: str = _DEFAULT_JWT_SECRET
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 480
    app_name: str = "MedVision API"
    debug: bool = False

    # Chemin de base pour le stockage des fichiers
    storage_base_path: str = os.path.join(os.path.sep, "data", "medvision", "exams")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    # Production guard : refuser la clé JWT par défaut si on n'est pas en debug
    if not settings.debug and settings.jwt_secret == _DEFAULT_JWT_SECRET:
        raise RuntimeError(
            "JWT_SECRET is still the default value. "
            "Set a secure secret via JWT_SECRET in .env or environment variables "
            "before running in production."
        )
    if settings.debug and settings.jwt_secret == _DEFAULT_JWT_SECRET:
        warnings.warn(
            "JWT_SECRET is using the default value — DO NOT RUN IN PRODUCTION."
        )
    return settings
