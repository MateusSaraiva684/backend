import uuid
import os
import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.models import Aluno, Usuario
from app.schemas.schemas import AlunoResponse
from app.routes.auth import get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)

EXTENSOES_PERMITIDAS = {"image/jpeg", "image/png", "image/webp"}
TAMANHO_MAXIMO = 5 * 1024 * 1024  # 5MB
PASTA_UPLOADS = "uploads/alunos"


def salvar_foto(foto: UploadFile) -> str | None:
    if not foto or not foto.filename:
        return None
    if foto.content_type not in EXTENSOES_PERMITIDAS:
        raise HTTPException(status_code=400, detail="Tipo de arquivo não permitido. Use JPEG, PNG ou WEBP.")
    conteudo = foto.file.read()
    if len(conteudo) > TAMANHO_MAXIMO:
        raise HTTPException(status_code=400, detail="Foto muito grande. Máximo 5MB.")
    extensao = foto.filename.rsplit(".", 1)[-1].lower()
    filename = f"{uuid.uuid4()}.{extensao}"
    os.makedirs(PASTA_UPLOADS, exist_ok=True)
    with open(f"{PASTA_UPLOADS}/{filename}", "wb") as f:
        f.write(conteudo)
    return f"/uploads/alunos/{filename}"


def require_admin(user: Usuario = Depends(get_current_user)):
    if not getattr(user, 'is_admin', False):
        raise HTTPException(status_code=403, detail="Acesso permitido apenas para administradores")
    return user


@router.get("/", response_model=List[AlunoResponse])
def listar(user: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Aluno).filter(Aluno.user_id == user.id).order_by(Aluno.id.desc()).all()


@router.get("/admin/usuarios/")
def listar_usuarios(db: Session = Depends(get_db), admin: Usuario = Depends(require_admin)):
    return db.query(Usuario).all()


@router.post("/", response_model=AlunoResponse, status_code=201)
def criar(
    nome: str = Form(...),
    telefone: str = Form(...),
    foto: UploadFile = File(None),
    user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    caminho = salvar_foto(foto)
    aluno = Aluno(nome=nome, telefone=telefone, foto=caminho, user_id=user.id)
    db.add(aluno)
    db.commit()
    db.refresh(aluno)
    logger.info("Aluno criado: id=%d por usuário id=%d", aluno.id, user.id)
    return aluno


@router.get("/{aluno_id}", response_model=AlunoResponse)
def buscar(aluno_id: int, user: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    aluno = db.query(Aluno).filter(Aluno.id == aluno_id, Aluno.user_id == user.id).first()
    if not aluno:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")
    return aluno


@router.put("/{aluno_id}", response_model=AlunoResponse)
def atualizar(
    aluno_id: int,
    nome: str = Form(...),
    telefone: str = Form(...),
    foto: UploadFile = File(None),
    user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    aluno = db.query(Aluno).filter(Aluno.id == aluno_id, Aluno.user_id == user.id).first()
    if not aluno:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")
    aluno.nome = nome
    aluno.telefone = telefone
    nova_foto = salvar_foto(foto)
    if nova_foto:
        aluno.foto = nova_foto
    db.commit()
    db.refresh(aluno)
    logger.info("Aluno atualizado: id=%d", aluno_id)
    return aluno


@router.delete("/{aluno_id}", status_code=204)
def deletar(aluno_id: int, user: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    aluno = db.query(Aluno).filter(Aluno.id == aluno_id, Aluno.user_id == user.id).first()
    if not aluno:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")
    db.delete(aluno)
    db.commit()
    logger.info("Aluno deletado: id=%d por usuário id=%d", aluno_id, user.id)
