import os
from dotenv import load_dotenv

load_dotenv()


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
    ADMIN_SECRET_KEY: str = os.getenv("ADMIN_SECRET_KEY", "")  # chave separada para tokens admin

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"


settings = Settings()

if settings.ENVIRONMENT not in ("testing",):
    if not settings.SECRET_KEY:
        raise RuntimeError("SECRET_KEY não definida nas variáveis de ambiente.")
    if not settings.DATABASE_URL:
        raise RuntimeError("DATABASE_URL não definida nas variáveis de ambiente.")
    if not settings.ADMIN_EMAIL or not settings.ADMIN_PASSWORD:
        raise RuntimeError("ADMIN_EMAIL e ADMIN_PASSWORD não definidos nas variáveis de ambiente.")
    if not settings.ADMIN_SECRET_KEY:
        raise RuntimeError("ADMIN_SECRET_KEY não definida nas variáveis de ambiente.")
