from dataclasses import dataclass

import httpx

from app.core.config import settings
from app.core.exceptions import AppError, BadRequestError, ServiceUnavailableError


@dataclass(frozen=True)
class FaceImagePayload:
    content: bytes | None = None
    filename: str | None = None
    content_type: str | None = None
    base64_image: str | None = None


@dataclass(frozen=True)
class FaceRecognitionResult:
    aluno_id: int
    confianca: float


class FaceRecognitionService:
    async def reconhecer(self, payload: FaceImagePayload) -> FaceRecognitionResult:
        if not settings.FACE_RECOGNITION_SERVICE_URL:
            raise ServiceUnavailableError("Servico de reconhecimento facial nao configurado")
        if not payload.content and not payload.base64_image:
            raise BadRequestError("Imagem nao fornecida")

        try:
            async with httpx.AsyncClient(
                timeout=settings.FACE_RECOGNITION_TIMEOUT_SECONDS
            ) as client:
                if payload.content:
                    files = {
                        "imagem": (
                            payload.filename or "imagem.jpg",
                            payload.content,
                            payload.content_type or "application/octet-stream",
                        )
                    }
                    response = await client.post(
                        settings.FACE_RECOGNITION_SERVICE_URL,
                        files=files,
                    )
                else:
                    response = await client.post(
                        settings.FACE_RECOGNITION_SERVICE_URL,
                        json={"imagem_base64": payload.base64_image},
                    )
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise AppError(504, "Servico de reconhecimento facial demorou para responder") from exc
        except httpx.HTTPStatusError as exc:
            raise AppError(
                502,
                f"Servico de reconhecimento facial retornou erro {exc.response.status_code}",
            ) from exc
        except httpx.HTTPError as exc:
            raise ServiceUnavailableError("Falha ao chamar servico de reconhecimento facial") from exc

        try:
            data = response.json()
        except ValueError as exc:
            raise AppError(502, "Resposta invalida do servico de reconhecimento facial") from exc

        try:
            confianca = float(data["confianca"])
            if not 0 <= confianca <= 1:
                raise ValueError("confianca fora da faixa esperada")
            return FaceRecognitionResult(
                aluno_id=int(data["aluno_id"]),
                confianca=confianca,
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise AppError(502, "Resposta invalida do servico de reconhecimento facial") from exc
