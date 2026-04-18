from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class Mensagem(BaseModel):
    mensagem: str


class ErroResponse(BaseModel):
    erro: str
    detalhe: Optional[str] = None


class RegistrarRequest(BaseModel):
    nome: str
    email: EmailStr
    senha: str


class LoginRequest(BaseModel):
    email: EmailStr
    senha: str


class RefreshRequest(BaseModel):
    refresh_token: str


class UsuarioResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    email: str
    is_superuser: bool
    criado_em: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    usuario: UsuarioResponse


class ResponsavelCreate(BaseModel):
    nome: str
    telefone: str
    email: Optional[EmailStr] = None


class ResponsavelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    telefone: str
    email: Optional[str] = None


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
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    numero_inscricao: str
    telefone: str
    turma: Optional[str] = None
    foto: Optional[str] = None
    criado_em: datetime
    user_id: int
    responsaveis: List[ResponsavelResponse] = Field(default_factory=list)


OrigemPresenca = Literal["manual", "facial"]
StatusPresenca = Literal["confirmado", "pendente", "erro"]


class PresencaManualCreate(BaseModel):
    aluno_id: int
    timestamp: Optional[datetime] = None
    status: StatusPresenca = "confirmado"

    @field_validator("timestamp")
    @classmethod
    def timestamp_deve_ter_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("timestamp deve incluir timezone")
        return value


class PresencaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    aluno_id: int
    timestamp: datetime
    origem: OrigemPresenca
    confianca: Optional[float] = None
    status: StatusPresenca


class ReconhecimentoFacialResponse(BaseModel):
    aluno_id: int
    confianca: float
    presenca: PresencaResponse
    mensagem: str


class FaceEmbeddingCreate(BaseModel):
    aluno_id: int
    embedding: List[float]


class FaceEmbeddingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    aluno_id: int
    embedding: List[float]
    criado_em: datetime


class AtualizarUsuarioRequest(BaseModel):
    nome: Optional[str] = None
    email: Optional[EmailStr] = None
    ativo: Optional[bool] = None


class RedefinirSenhaRequest(BaseModel):
    nova_senha: str


class PaginacaoMetadata(BaseModel):
    """Metadata de paginação."""
    total: int
    pagina: int
    limite: int
    paginas_totais: int
    proxima_pagina: Optional[int] = None


class PaginadoResponse(BaseModel):
    """Resposta paginada genérica."""
    data: List[AlunoResponse]
    paginacao: PaginacaoMetadata
