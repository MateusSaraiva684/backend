import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from jose import JWTError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import BadRequestError, UnauthorizedError
from app.core.security import (
    criar_access_token,
    criar_refresh_token,
    decodificar_access_token,
    hash_senha,
    verificar_senha,
)
from app.models.models import RefreshToken, Usuario
from app.repositories.usuario_repository import RefreshTokenRepository, UsuarioRepository
from app.schemas.schemas import LoginRequest, RegistrarRequest

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TokenBundle:
    access_token: str
    refresh_token: str
    expires_in: int
    usuario: Usuario


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.usuarios = UsuarioRepository(db)
        self.refresh_tokens = RefreshTokenRepository(db)

    def registrar(self, body: RegistrarRequest) -> None:
        if self.usuarios.get_by_email(body.email):
            raise BadRequestError("E-mail já cadastrado")
        if len(body.senha) < 6:
            raise BadRequestError("Senha deve ter no minimo 6 caracteres")

        usuario = Usuario(nome=body.nome, email=body.email, senha=hash_senha(body.senha))
        self.usuarios.add(usuario)
        self.db.commit()
        logger.info("Novo usuario registrado: %s", body.email)

    def autenticar(self, body: LoginRequest) -> Usuario:
        user = self.usuarios.get_by_email(body.email, ativo=True)

        if not user:
            if body.email == settings.ADMIN_EMAIL and body.senha == settings.ADMIN_PASSWORD:
                user = Usuario(
                    nome="Administrador",
                    email=settings.ADMIN_EMAIL,
                    senha=hash_senha(settings.ADMIN_PASSWORD),
                    is_superuser=True,
                    ativo=True,
                )
                self.usuarios.add(user)
                self.db.commit()
                self.db.refresh(user)
                logger.info("Admin criado automaticamente via login fallback: %s", body.email)
                return user
            raise UnauthorizedError("E-mail ou senha incorretos")

        if not verificar_senha(body.senha, user.senha):
            if body.email == settings.ADMIN_EMAIL and body.senha == settings.ADMIN_PASSWORD:
                user.senha = hash_senha(settings.ADMIN_PASSWORD)
                user.is_superuser = True
                user.ativo = True
                self.db.commit()
                logger.info("Admin sincronizado automaticamente via login fallback: %s", body.email)
                return user
            raise UnauthorizedError("E-mail ou senha incorretos")

        logger.info("Login realizado: %s", body.email)
        return user

    def emitir_tokens(self, user: Usuario) -> TokenBundle:
        access_token = criar_access_token(user.id)
        refresh_token = criar_refresh_token()
        rt = RefreshToken(
            token=refresh_token,
            user_id=user.id,
            expira_em=datetime.now(timezone.utc)
            + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )
        self.refresh_tokens.add(rt)
        self.db.commit()
        return TokenBundle(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            usuario=user,
        )

    def renovar(self, token: str | None) -> TokenBundle:
        if not token:
            raise UnauthorizedError("Refresh token nao fornecido")

        rt = self.refresh_tokens.get_by_token(token)
        if not rt or not rt.valido:
            raise UnauthorizedError("Refresh token invalido ou expirado")

        rt.revogado = True
        self.db.commit()

        user = rt.usuario
        if not user.ativo:
            raise UnauthorizedError("Usuario inativo")

        logger.info("Token renovado para usuario id=%d", user.id)
        return self.emitir_tokens(user)

    def revogar_refresh_token(self, token: str | None) -> None:
        if not token:
            return
        rt = self.refresh_tokens.get_by_token(token)
        if rt:
            rt.revogado = True
            self.db.commit()

    def get_current_user_from_token(self, token: str) -> Usuario:
        try:
            payload = decodificar_access_token(token)
            user_id = int(payload["sub"])
        except (JWTError, KeyError, ValueError) as exc:
            raise UnauthorizedError("Token invalido ou expirado") from exc

        user = self.usuarios.get_by_id(user_id, ativo=True)
        if not user:
            raise UnauthorizedError("Usuario nao encontrado")
        return user
