from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.models import Usuario
from app.routes.auth import get_current_user
from app.schemas.schemas import AlunoResponse
from app.services.aluno_service import AlunoService

router = APIRouter()


def get_aluno_service(db: Session = Depends(get_db)) -> AlunoService:
    return AlunoService(db)


@router.get("/turmas", response_model=List[str])
def listar_turmas(
    user: Usuario = Depends(get_current_user),
    service: AlunoService = Depends(get_aluno_service),
):
    return service.listar_turmas(user)


@router.get("/", response_model=List[AlunoResponse])
def listar(
    turma: Optional[str] = None,
    busca: Optional[str] = None,
    user: Usuario = Depends(get_current_user),
    service: AlunoService = Depends(get_aluno_service),
):
    return service.listar(user, turma=turma, busca=busca)


@router.post("/", response_model=AlunoResponse, status_code=201)
def criar(
    nome: str = Form(...),
    numero_inscricao: str = Form(...),
    telefone: str = Form(...),
    turma: str = Form(""),
    foto: UploadFile = File(None),
    user: Usuario = Depends(get_current_user),
    service: AlunoService = Depends(get_aluno_service),
):
    return service.criar(
        user=user,
        nome=nome,
        numero_inscricao=numero_inscricao,
        telefone=telefone,
        turma=turma,
        foto=foto,
    )


@router.get("/{aluno_id}", response_model=AlunoResponse)
def buscar(
    aluno_id: int,
    user: Usuario = Depends(get_current_user),
    service: AlunoService = Depends(get_aluno_service),
):
    return service.buscar(user, aluno_id)


@router.put("/{aluno_id}", response_model=AlunoResponse)
def atualizar(
    aluno_id: int,
    nome: str = Form(...),
    numero_inscricao: str = Form(...),
    telefone: str = Form(...),
    turma: str = Form(""),
    foto: UploadFile = File(None),
    user: Usuario = Depends(get_current_user),
    service: AlunoService = Depends(get_aluno_service),
):
    return service.atualizar(
        user=user,
        aluno_id=aluno_id,
        nome=nome,
        numero_inscricao=numero_inscricao,
        telefone=telefone,
        turma=turma,
        foto=foto,
    )


@router.delete("/{aluno_id}", status_code=204)
def deletar(
    aluno_id: int,
    user: Usuario = Depends(get_current_user),
    service: AlunoService = Depends(get_aluno_service),
):
    service.deletar(user, aluno_id)
