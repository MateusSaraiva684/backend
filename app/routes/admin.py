import logging
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import jwt, JWTError
from typing import Optional

from app.database.session import get_db
from app.models.models import Usuario, Aluno
from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)
bearer = HTTPBearer(auto_error=False)

ADMIN_TOKEN_EXPIRE_HOURS = 8


# ── Token admin (chave separada da chave dos usuários) ────────────────────────

def _criar_token_admin() -> str:
    agora = datetime.now(timezone.utc)
    expire = agora + timedelta(hours=ADMIN_TOKEN_EXPIRE_HOURS)
    payload = {"sub": "admin", "type": "admin", "exp": expire, "iat": agora}
    return jwt.encode(payload, settings.ADMIN_SECRET_KEY, algorithm=settings.ALGORITHM)


def _verificar_token_admin(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer),
) -> str:
    if not credentials:
        raise HTTPException(status_code=401, detail="Token admin não fornecido")
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.ADMIN_SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        if payload.get("type") != "admin":
            raise JWTError("Tipo inválido")
        return payload["sub"]
    except JWTError:
        raise HTTPException(status_code=401, detail="Token admin inválido ou expirado")


# ── Login admin ───────────────────────────────────────────────────────────────

from pydantic import BaseModel

class AdminLoginRequest(BaseModel):
    email: str
    senha: str

class AdminTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


@router.post("/login", response_model=AdminTokenResponse)
def admin_login(body: AdminLoginRequest):
    if body.email != settings.ADMIN_EMAIL or body.senha != settings.ADMIN_PASSWORD:
        logger.warning("Tentativa de login admin falhou para email: %s", body.email)
        raise HTTPException(status_code=401, detail="Credenciais de administrador inválidas")

    token = _criar_token_admin()
    logger.info("Login admin realizado")
    return AdminTokenResponse(
        access_token=token,
        expires_in=ADMIN_TOKEN_EXPIRE_HOURS * 3600,
    )


# ── Usuários ──────────────────────────────────────────────────────────────────

@router.get("/usuarios")
def listar_usuarios(
    db: Session = Depends(get_db),
    _: str = Depends(_verificar_token_admin),
):
    usuarios = db.query(Usuario).order_by(Usuario.id.desc()).all()
    return [
        {
            "id": u.id,
            "nome": u.nome,
            "email": u.email,
            "ativo": u.ativo,
            "criado_em": u.criado_em,
            "total_alunos": db.query(Aluno).filter(Aluno.user_id == u.id).count(),
        }
        for u in usuarios
    ]


@router.patch("/usuarios/{usuario_id}/ativo")
def toggle_usuario_ativo(
    usuario_id: int,
    db: Session = Depends(get_db),
    _: str = Depends(_verificar_token_admin),
):
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    usuario.ativo = not usuario.ativo
    db.commit()
    status_str = "ativado" if usuario.ativo else "desativado"
    logger.info("Usuário id=%d %s pelo admin", usuario_id, status_str)
    return {"id": usuario.id, "ativo": usuario.ativo, "mensagem": f"Usuário {status_str}"}


@router.delete("/usuarios/{usuario_id}")
def deletar_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    _: str = Depends(_verificar_token_admin),
):
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    db.delete(usuario)
    db.commit()
    logger.info("Usuário id=%d deletado pelo admin", usuario_id)
    return {"mensagem": "Usuário removido com sucesso"}


# ── Alunos (todos os usuários) ────────────────────────────────────────────────

@router.get("/alunos")
def listar_todos_alunos(
    db: Session = Depends(get_db),
    _: str = Depends(_verificar_token_admin),
):
    alunos = (
        db.query(Aluno, Usuario.nome.label("usuario_nome"), Usuario.email.label("usuario_email"))
        .join(Usuario, Aluno.user_id == Usuario.id)
        .order_by(Aluno.id.desc())
        .all()
    )
    return [
        {
            "id": a.Aluno.id,
            "nome": a.Aluno.nome,
            "telefone": a.Aluno.telefone,
            "foto": a.Aluno.foto,
            "criado_em": a.Aluno.criado_em,
            "usuario_nome": a.usuario_nome,
            "usuario_email": a.usuario_email,
        }
        for a in alunos
    ]


# ── Estatísticas ──────────────────────────────────────────────────────────────

@router.get("/stats")
def estatisticas(
    db: Session = Depends(get_db),
    _: str = Depends(_verificar_token_admin),
):
    total_usuarios = db.query(Usuario).count()
    usuarios_ativos = db.query(Usuario).filter(Usuario.ativo == True).count()
    total_alunos = db.query(Aluno).count()

    return {
        "total_usuarios": total_usuarios,
        "usuarios_ativos": usuarios_ativos,
        "usuarios_inativos": total_usuarios - usuarios_ativos,
        "total_alunos": total_alunos,
    }
