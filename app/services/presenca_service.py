import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.models import Presenca, Usuario
from app.repositories.presenca_repository import PresencaRepository
from app.schemas.schemas import PresencaManualCreate
from app.services.aluno_service import AlunoService
from app.services.face_recognition_service import FaceRecognitionResult
from app.services.notification_service import NotificationService

logger = logging.getLogger(__name__)


class PresencaService:
    def __init__(
        self,
        db: Session,
        notification_service: NotificationService | None = None,
    ):
        self.db = db
        self.presencas = PresencaRepository(db)
        self.alunos = AlunoService(db)
        self.notification_service = notification_service or NotificationService()

    def registrar_manual(self, body: PresencaManualCreate, user: Usuario) -> Presenca:
        self.alunos.buscar_para_usuario_ou_admin(user, body.aluno_id)
        presenca = Presenca(
            aluno_id=body.aluno_id,
            timestamp=body.timestamp or datetime.now(timezone.utc),
            origem="manual",
            confianca=None,
            status=body.status,
        )
        self.presencas.add(presenca)
        self.db.commit()
        self.db.refresh(presenca)
        logger.info("Presenca manual registrada: id=%d aluno_id=%d", presenca.id, body.aluno_id)
        return presenca

    def listar_por_aluno(self, aluno_id: int, user: Usuario) -> list[Presenca]:
        self.alunos.buscar_para_usuario_ou_admin(user, aluno_id)
        return self.presencas.list_by_aluno(aluno_id)

    def registrar_por_reconhecimento(
        self,
        resultado: FaceRecognitionResult,
        user: Usuario,
    ) -> Presenca:
        aluno = self.alunos.buscar_para_usuario_ou_admin(user, resultado.aluno_id)
        presenca = Presenca(
            aluno_id=resultado.aluno_id,
            timestamp=datetime.now(timezone.utc),
            origem="facial",
            confianca=resultado.confianca,
            status="confirmado",
        )
        self.presencas.add(presenca)
        self.db.commit()
        self.db.refresh(presenca)

        mensagem = f"Presenca registrada para {aluno.nome}."
        for responsavel in aluno.responsaveis:
            self.notification_service.enviar_presenca(responsavel, mensagem)

        logger.info(
            "Presenca facial registrada: id=%d aluno_id=%d confianca=%.4f",
            presenca.id,
            resultado.aluno_id,
            resultado.confianca,
        )
        return presenca
