from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.models import Usuario
from app.routes.auth import get_current_user
from app.schemas.schemas import PresencaManualCreate, PresencaResponse
from app.services.presenca_service import PresencaService

router = APIRouter()


def get_presenca_service(db: Session = Depends(get_db)) -> PresencaService:
    return PresencaService(db)


@router.post("/manual", response_model=PresencaResponse, status_code=201)
def registrar_manual(
    body: PresencaManualCreate,
    user: Usuario = Depends(get_current_user),
    service: PresencaService = Depends(get_presenca_service),
):
    return service.registrar_manual(body, user)


@router.get("/aluno/{aluno_id}", response_model=List[PresencaResponse])
def listar_por_aluno(
    aluno_id: int,
    user: Usuario = Depends(get_current_user),
    service: PresencaService = Depends(get_presenca_service),
):
    return service.listar_por_aluno(aluno_id, user)
