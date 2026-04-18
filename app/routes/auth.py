import logging
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Response, Cookie
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import JWTError
from typing import Optional

from app.database.session import get_db
from app.models.models import Usuario, RefreshToken
from app.schemas.schemas import (
    RegistrarRequest, LoginRequest, TokenResponse,
    RefreshRequest, UsuarioResponse, Mensagem
)
from app.core.security import (
    hash_senha, verificar_senha,
    criar_access_token, criar_refresh_token, decodificar_access_token
)
from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)
bearer = HTTPBearer(auto_error=False)


# ── Dependência: usuário autenticado ─────────────────────────────────────────

def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer),
    db: Session = Depends(get_db),
) -> Usuario:
    if not credentials:
        raise HTTPException(status_code=401, detail="Token não fornecido")
    try:
        payload = decodificar_access_token(credentials.credentials)
        user_id = int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise HTTPException(status_code=401, detail="Token inválido ou expirado")

    user = db.query(Usuario).filter(Usuario.id == user_id, Usuario.ativo == True).first()
    if not user:
        raise HTTPException(status_code=401, detail="Usuário não encontrado")
    return user


def _salvar_refresh_token(db: Session, user_id: int, token: str):
    rt = RefreshToken(
        token=token,
        user_id=user_id,
        expira_em=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(rt)
    db.commit()


def _set_refresh_cookie(response: Response, token: str):
    response.set_cookie(
        key="refresh_token",
        value=token,
        httponly=True,
        secure=settings.is_production,
        samesite="none" if settings.is_production else "lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        path="/api/auth",
    )


def _montar_token_response(user: Usuario, db: Session, response: Response) -> dict:
    access_token = criar_access_token(user.id)
    refresh_token = criar_refresh_token()
    _salvar_refresh_token(db, user.id, refresh_token)
    _set_refresh_cookie(response, refresh_token)
    return {
        "access_token": access_token,
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "usuario": user,
    }


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/registrar", response_model=Mensagem, status_code=201)
def registrar(body: RegistrarRequest, db: Session = Depends(get_db)):
    if db.query(Usuario).filter(Usuario.email == body.email).first():
        raise HTTPException(status_code=400, detail="E-mail já cadastrado")
    if len(body.senha) < 6:
        raise HTTPException(status_code=400, detail="Senha deve ter no mínimo 6 caracteres")

    novo = Usuario(nome=body.nome, email=body.email, senha=hash_senha(body.senha))
    db.add(novo)
    db.commit()

    logger.info("Novo usuário registrado: %s", body.email)
    return {"mensagem": "Conta criada com sucesso"}


# � LOGIN
@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = db.query(Usuario).filter(
        Usuario.email == body.email,
        Usuario.ativo == True
    ).first()

    if not user:
        # Se o admin ainda não existe no banco, podemos criar automaticamente quando as credenciais vierem de .env.
        if (body.email == settings.ADMIN_EMAIL and body.senha == settings.ADMIN_PASSWORD):
            user = Usuario(
                nome="Administrador",
                email=settings.ADMIN_EMAIL,
                senha=hash_senha(settings.ADMIN_PASSWORD),
                is_superuser=True,
                ativo=True,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            logger.info("Admin criado automaticamente via login fallback: %s", body.email)
        else:
            raise HTTPException(status_code=401, detail="E-mail ou senha incorretos")

    if not verificar_senha(body.senha, user.senha):
        if body.email == settings.ADMIN_EMAIL and body.senha == settings.ADMIN_PASSWORD:
            # Se a senha do admin corresponde ao .env mas o hash no banco está desatualizado,
            # atualizamos o registro e permitimos o login.
            user.senha = hash_senha(settings.ADMIN_PASSWORD)
            user.is_superuser = True
            user.ativo = True
            db.commit()
            logger.info("Admin sincronizado automaticamente via login fallback: %s", body.email)
        else:
            raise HTTPException(status_code=401, detail="E-mail ou senha incorretos")

    logger.info("Login realizado: %s", body.email)
    return _montar_token_response(user, db, response)


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    response: Response,
    db: Session = Depends(get_db),
    cookie_token: Optional[str] = Cookie(default=None, alias="refresh_token"),
    body: Optional[RefreshRequest] = None,
):
    token = cookie_token or (body.refresh_token if body else None)
    if not token:
        raise HTTPException(status_code=401, detail="Refresh token não fornecido")

    rt = db.query(RefreshToken).filter(RefreshToken.token == token).first()
    if not rt or not rt.valido:
        raise HTTPException(status_code=401, detail="Refresh token inválido ou expirado")

    rt.revogado = True
    db.commit()

    user = rt.usuario
    if not user.ativo:
        raise HTTPException(status_code=401, detail="Usuário inativo")

    logger.info("Token renovado para usuário id=%d", user.id)
    return _montar_token_response(user, db, response)


@router.post("/logout", response_model=Mensagem)
def logout(
    response: Response,
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
    cookie_token: Optional[str] = Cookie(default=None, alias="refresh_token"),
):
    if cookie_token:
        rt = db.query(RefreshToken).filter(RefreshToken.token == cookie_token).first()
        if rt:
            rt.revogado = True
            db.commit()

    response.delete_cookie(
        key="refresh_token",
        path="/api/auth",
        samesite="none" if settings.is_production else "lax",
        secure=settings.is_production,
    )

    logger.info("Logout: usuário id=%d", user.id)
    return {"mensagem": "Logout realizado com sucesso"}


@router.get("/me", response_model=UsuarioResponse)
def me(user: Usuario = Depends(get_current_user)):
    return user