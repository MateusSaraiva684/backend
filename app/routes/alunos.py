import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
import cloudinary
import cloudinary.uploader

from app.database.session import get_db
from app.models.models import Aluno, Usuario
from app.schemas.schemas import AlunoResponse
from app.routes.auth import get_current_user
from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

EXTENSOES_PERMITIDAS = {"image/jpeg", "image/png", "image/webp"}
TAMANHO_MAXIMO = 5 * 1024 * 1024  # 5MB

# Configura Cloudinary com as credenciais do .env
cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET,
    secure=True,
)


def salvar_foto(foto: UploadFile) -> str | None:
    """Faz upload da foto para o Cloudinary e retorna a URL segura."""
    if not foto or not foto.filename:
        return None
    if foto.content_type not in EXTENSOES_PERMITIDAS:
        raise HTTPException(status_code=400, detail="Tipo de arquivo não permitido. Use JPEG, PNG ou WEBP.")
    conteudo = foto.file.read()
    if len(conteudo) > TAMANHO_MAXIMO:
        raise HTTPException(status_code=400, detail="Foto muito grande. Máximo 5MB.")

    try:
        resultado = cloudinary.uploader.upload(
            conteudo,
            folder="sistema_escolar/alunos",
            resource_type="image",
            transformation=[{"width": 400, "height": 400, "crop": "fill", "gravity": "face"}],
        )
        return resultado["secure_url"]
    except Exception as e:
        logger.error("Erro ao fazer upload para Cloudinary: %s", e)
        raise HTTPException(status_code=500, detail="Erro ao salvar a foto. Tente novamente.")


def deletar_foto_cloudinary(url: str | None):
    """Remove a foto antiga do Cloudinary ao atualizar ou deletar um aluno."""
    if not url or "cloudinary.com" not in url:
        return
    try:
        # Extrai o public_id da URL (ex: sistema_escolar/alunos/abc123)
        partes = url.split("/upload/")
        if len(partes) == 2:
            public_id_com_ext = partes[1]
            # Remove versão se existir (ex: v1234567890/)
            if public_id_com_ext.startswith("v") and "/" in public_id_com_ext:
                public_id_com_ext = public_id_com_ext.split("/", 1)[1]
            public_id = public_id_com_ext.rsplit(".", 1)[0]
            cloudinary.uploader.destroy(public_id)
    except Exception as e:
        logger.warning("Não foi possível deletar foto do Cloudinary: %s", e)


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
    nova_url = salvar_foto(foto)
    if nova_url:
        deletar_foto_cloudinary(aluno.foto)  # remove a foto antiga
        aluno.foto = nova_url
    db.commit()
    db.refresh(aluno)
    logger.info("Aluno atualizado: id=%d", aluno_id)
    return aluno


@router.delete("/{aluno_id}", status_code=204)
def deletar(aluno_id: int, user: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    aluno = db.query(Aluno).filter(Aluno.id == aluno_id, Aluno.user_id == user.id).first()
    if not aluno:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")
    deletar_foto_cloudinary(aluno.foto)  # remove do Cloudinary ao deletar
    db.delete(aluno)
    db.commit()
    logger.info("Aluno deletado: id=%d por usuário id=%d", aluno_id, user.id)
