import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.models import Aluno, Usuario
from app.routes.auth import get_current_user
from app.schemas.schemas import AlunoResponse
from app.services.media import deletar_foto_cloudinary, salvar_foto

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/", response_model=List[AlunoResponse])
def listar(user: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Aluno).filter(Aluno.user_id == user.id).order_by(Aluno.id.desc()).all()


@router.post("/", response_model=AlunoResponse, status_code=201)
def criar(
    nome: str = Form(...),
    telefone: str = Form(...),
    foto: UploadFile = File(None),
    user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    url_foto = salvar_foto(foto)
    aluno = Aluno(nome=nome, telefone=telefone, foto=url_foto, user_id=user.id)
    db.add(aluno)
    db.commit()
    db.refresh(aluno)
    logger.info("Aluno criado: id=%d por usuario id=%d", aluno.id, user.id)
    return aluno


@router.get("/{aluno_id}", response_model=AlunoResponse)
def buscar(aluno_id: int, user: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    aluno = db.query(Aluno).filter(Aluno.id == aluno_id, Aluno.user_id == user.id).first()
    if not aluno:
        raise HTTPException(status_code=404, detail="Aluno nao encontrado")
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
        raise HTTPException(status_code=404, detail="Aluno nao encontrado")

    aluno.nome = nome
    aluno.telefone = telefone

    nova_url = salvar_foto(foto)
    if nova_url:
        deletar_foto_cloudinary(aluno.foto)
        aluno.foto = nova_url

    db.commit()
    db.refresh(aluno)
    logger.info("Aluno atualizado: id=%d", aluno_id)
    return aluno


@router.delete("/{aluno_id}", status_code=204)
def deletar(aluno_id: int, user: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    aluno = db.query(Aluno).filter(Aluno.id == aluno_id, Aluno.user_id == user.id).first()
    if not aluno:
        raise HTTPException(status_code=404, detail="Aluno nao encontrado")

    deletar_foto_cloudinary(aluno.foto)
    db.delete(aluno)
    db.commit()
    logger.info("Aluno deletado: id=%d por usuario id=%d", aluno_id, user.id)
