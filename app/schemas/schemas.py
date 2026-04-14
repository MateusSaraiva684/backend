from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


# ── Respostas padronizadas ────────────────────────────────────────────────────

class Mensagem(BaseModel):
    mensagem: str


class ErroResponse(BaseModel):
    erro: str
    detalhe: Optional[str] = None


# ── Auth ──────────────────────────────────────────────────────────────────────

class RegistrarRequest(BaseModel):
    nome: str
    email: EmailStr
    senha: str

class LoginRequest(BaseModel):
    email: EmailStr
    senha: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # segundos
    usuario: "UsuarioResponse"

class RefreshRequest(BaseModel):
    refresh_token: str

class UsuarioResponse(BaseModel):
    id: int
    nome: str
    email: str
    is_superuser: bool
    criado_em: datetime

    class Config:
        from_attributes = True


# ── Aluno ─────────────────────────────────────────────────────────────────────

class AlunoCreate(BaseModel):
    nome: str
    numero_inscricao: str
    telefone: str
    turma: Optional[str] = None

class AlunoUpdate(BaseModel):
    nome: str
    numero_inscricao: str
    telefone: str
    turma: Optional[str] = None

class AlunoResponse(BaseModel):
    id: int
    nome: str
    numero_inscricao: str
    telefone: str
    turma: Optional[str] = None
    foto: Optional[str] = None
    criado_em: datetime
    user_id: int

    class Config:
        from_attributes = True


TokenResponse.model_rebuild()
