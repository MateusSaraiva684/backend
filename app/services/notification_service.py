import logging

from app.models.models import Responsavel

logger = logging.getLogger(__name__)


class NotificationService:
    def enviar_presenca(self, responsavel: Responsavel, mensagem: str) -> None:
        logger.info(
            "Notificacao de presenca enviada para responsavel id=%d telefone=%s: %s",
            responsavel.id,
            responsavel.telefone,
            mensagem,
        )
