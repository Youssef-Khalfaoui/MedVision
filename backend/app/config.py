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

# Secrets matching any of these are rejected outside debug mode, so copying
# .env.example verbatim cannot silently ship a guessable secret.
_WEAK_SECRET_MARKERS = (
    "changeme", "change-me", "change_me", "your-", "example",
    "dummy", "placeholder", "use-a-real",
)


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://medvision:medvision_dev@localhost:5432/medvision"
    db_host: str = "localhost"
    db_port: int = 5433
    db_name: str = "medvision"
    db_user: str = "medvision"
    db_password: str = "medvisionpass"

    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str = ""

    ai_api_url: str = "http://localhost:8002/analyze"

    # Production : mettre JWT_SECRET dans .env / variables d'environnement.
    # Si non défini, un avertissement est émis au démarrage.
    jwt_secret: str = _DEFAULT_JWT_SECRET
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 480
    app_name: str = "MedVision API"
    debug: bool = False

    # Browser origins allowed by CORS (comma-separated). Never put "*" here:
    # combined with allow_credentials=True it lets any website make
    # credentialed calls against the API.
    allowed_origins: str = (
        "http://localhost:5173,http://localhost:8080,"
        "http://127.0.0.1:5173,http://127.0.0.1:8080"
    )

    # Chemin de base pour le stockage des fichiers
    storage_base_path: str = os.path.join(os.path.sep, "data", "medvision", "exams")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    @property
    def cors_origins(self) -> list:
        """Parsed CORS origin list. '*' is refused outside debug mode."""
        origins = [o.strip() for o in self.allowed_origins.split(",") if o.strip()]
        if "*" in origins and not self.debug:
            raise RuntimeError(
                "ALLOWED_ORIGINS contains '*' which is not allowed outside "
                "debug mode. List the actual frontend origins instead."
            )
        return origins

    @property
    def jwt_secret_is_weak(self) -> bool:
        """True for short secrets or secrets copied from an example file."""
        return (
            len(self.jwt_secret) < 32
            or any(marker in self.jwt_secret.lower() for marker in _WEAK_SECRET_MARKERS)
        )


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    # Production guard : refuser les secrets par défaut, faibles ou copiés
    # depuis .env.example (fail closed — l'application ne démarre pas).
    if not settings.debug and (
        settings.jwt_secret == _DEFAULT_JWT_SECRET or settings.jwt_secret_is_weak
    ):
        raise RuntimeError(
            "JWT_SECRET is missing, too short (<32 chars) or copied from an "
            "example file. Generate a strong secret with:\n"
            '  python -c "import secrets; print(secrets.token_urlsafe(48))"\n'
            "then set JWT_SECRET in .env or the environment."
        )
    if settings.debug and (
        settings.jwt_secret == _DEFAULT_JWT_SECRET or settings.jwt_secret_is_weak
    ):
        warnings.warn(
            "JWT_SECRET is using a weak/default value — DO NOT RUN IN PRODUCTION."
        )
    return settings

