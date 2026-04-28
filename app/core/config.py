import os
from dotenv import load_dotenv

load_dotenv()


def _env_flag(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "sim", "on")


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        parsed = float(value)
    except ValueError as exc:
        raise RuntimeError(f"{name} deve ser um numero valido.") from exc
    if parsed <= 0:
        raise RuntimeError(f"{name} deve ser maior que zero.")
    return parsed


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        parsed = int(value)
    except ValueError as exc:
        raise RuntimeError(f"{name} deve ser um numero inteiro valido.") from exc
    if parsed <= 0:
        raise RuntimeError(f"{name} deve ser maior que zero.")
    return parsed


class Settings:
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

    # Credenciais do painel admin (definidas nas variáveis de ambiente)
    ADMIN_EMAIL: str = os.getenv("ADMIN_EMAIL", "")
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "")
    ADMIN_SECRET_KEY: str = os.getenv("ADMIN_SECRET_KEY", "")  # mantida por compatibilidade

    # Cloudinary — armazenamento de fotos
    CLOUDINARY_CLOUD_NAME: str = os.getenv("CLOUDINARY_CLOUD_NAME", "")
    CLOUDINARY_API_KEY: str = os.getenv("CLOUDINARY_API_KEY", "")
    CLOUDINARY_API_SECRET: str = os.getenv("CLOUDINARY_API_SECRET", "")

    FACE_RECOGNITION_SERVICE_URL: str = os.getenv("FACE_RECOGNITION_SERVICE_URL", "")
    FACE_RECOGNITION_TIMEOUT_SECONDS: float = _env_float(
        "FACE_RECOGNITION_TIMEOUT_SECONDS", 10
    )
    MAX_IMAGE_UPLOAD_BYTES: int = _env_int("MAX_IMAGE_UPLOAD_BYTES", 5 * 1024 * 1024)

    REDIS_URL: str = os.getenv("REDIS_URL", "")
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", "")
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", "")
    TRUST_PROXY_HEADERS: bool = _env_flag("TRUST_PROXY_HEADERS", False)

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def sync_admin_password_on_startup(self) -> bool:
        return _env_flag("SYNC_ADMIN_PASSWORD_ON_STARTUP", not self.is_production)


settings = Settings()

if settings.ENVIRONMENT not in ("testing",):
    if not settings.SECRET_KEY:
        raise RuntimeError("SECRET_KEY não definida nas variáveis de ambiente.")
    if not settings.DATABASE_URL:
        raise RuntimeError("DATABASE_URL não definida nas variáveis de ambiente.")
    if not settings.ADMIN_EMAIL or not settings.ADMIN_PASSWORD:
        raise RuntimeError("ADMIN_EMAIL e ADMIN_PASSWORD não definidos nas variáveis de ambiente.")
