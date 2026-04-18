from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
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


@router.get("/", response_model=dict)
def listar(
    turma: Optional[str] = None,
    busca: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    user: Usuario = Depends(get_current_user),
    service: AlunoService = Depends(get_aluno_service),
):
    """Lista alunos com paginação.
    
    Parâmetros:
    - page: Número da página (padrão: 1)
    - limit: Itens por página (padrão: 50, máximo: 100)
    - turma: Filtrar por turma (opcional)
    - busca: Buscar por nome ou número de inscrição (opcional)
    """
    return service.listar(user, turma=turma, busca=busca, page=page, limit=limit)


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
