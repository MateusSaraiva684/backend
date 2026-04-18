from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey,
    DateTime,
    Boolean,
    UniqueConstraint,
    Float,
    JSON,
    Table,
)
from sqlalchemy.orm import relationship
from app.database.session import Base


aluno_responsaveis = Table(
    "aluno_responsaveis",
    Base.metadata,
    Column("aluno_id", ForeignKey("alunos.id", ondelete="CASCADE"), primary_key=True),
    Column("responsavel_id", ForeignKey("responsaveis.id", ondelete="CASCADE"), primary_key=True),
)


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    senha = Column(String, nullable=False)
    ativo = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    criado_em = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    alunos = relationship("Aluno", back_populates="usuario", cascade="all, delete-orphan")
    refresh_tokens = relationship("RefreshToken", back_populates="usuario", cascade="all, delete-orphan")


class Aluno(Base):
    __tablename__ = "alunos"
    __table_args__ = (
        UniqueConstraint("user_id", "numero_inscricao", name="uq_alunos_user_numero_inscricao"),
    )

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    numero_inscricao = Column(String, nullable=False)
    telefone = Column(String, nullable=False)
    turma = Column(String, nullable=True)
    foto = Column(String, nullable=True)
    criado_em = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    usuario = relationship("Usuario", back_populates="alunos")
    responsaveis = relationship(
        "Responsavel",
        secondary=aluno_responsaveis,
        back_populates="alunos",
    )
    presencas = relationship("Presenca", back_populates="aluno", cascade="all, delete-orphan")
    face_embeddings = relationship("FaceEmbedding", back_populates="aluno", cascade="all, delete-orphan")


class Responsavel(Base):
    __tablename__ = "responsaveis"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    telefone = Column(String, nullable=False)
    email = Column(String, nullable=True)

    alunos = relationship(
        "Aluno",
        secondary=aluno_responsaveis,
        back_populates="responsaveis",
    )


class Presenca(Base):
    __tablename__ = "presencas"

    id = Column(Integer, primary_key=True, index=True)
    aluno_id = Column(Integer, ForeignKey("alunos.id", ondelete="CASCADE"), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    origem = Column(String, nullable=False)
    confianca = Column(Float, nullable=True)
    status = Column(String, nullable=False, default="confirmado")

    aluno = relationship("Aluno", back_populates="presencas")


class FaceEmbedding(Base):
    __tablename__ = "face_embeddings"

    id = Column(Integer, primary_key=True, index=True)
    aluno_id = Column(Integer, ForeignKey("alunos.id", ondelete="CASCADE"), nullable=False, index=True)
    embedding = Column(JSON, nullable=False)
    criado_em = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    aluno = relationship("Aluno", back_populates="face_embeddings")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String, unique=True, index=True, nullable=False)
    expira_em = Column(DateTime(timezone=True), nullable=False)
    revogado = Column(Boolean, default=False, nullable=False)
    criado_em = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    usuario = relationship("Usuario", back_populates="refresh_tokens")

    @property
    def expirado(self) -> bool:
        expira_em = self.expira_em
        if expira_em.tzinfo is None:
            expira_em = expira_em.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) > expira_em

    @property
    def valido(self) -> bool:
        return not self.revogado and not self.expirado
