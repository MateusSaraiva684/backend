import secrets
from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
from jose import jwt
from app.core.config import settings
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def hash_senha(senha: str) -> str:
    return pwd_context.hash(senha)


def verificar_senha(senha: str, hash: str) -> bool:
    return pwd_context.verify(senha, hash)


def criar_access_token(user_id: int) -> str:
    agora = datetime.now(timezone.utc)
    expire = agora + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "type": "access", "exp": expire, "iat": agora}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def criar_refresh_token() -> str:
    """Gera um refresh token opaco e aleatório (256 bits)."""
    return secrets.token_hex(32)


def decodificar_access_token(token: str) -> dict:
    """Decodifica e valida o access token. Lança JWTError se inválido."""
    from jose import JWTError
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    if payload.get("type") != "access":
        raise JWTError("Tipo de token inválido")
    return payload

def get_current_user(token: str = Depends(oauth2_scheme)):
    payload = decodificar_access_token(token)
    user_id = payload.get("sub")
    # TODO: Buscar usuário no banco de dados
    return {"id": user_id, "is_admin": False}


def require_admin(user=Depends(get_current_user)):
    if not user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Acesso permitido apenas para administradores"
        )
    return user