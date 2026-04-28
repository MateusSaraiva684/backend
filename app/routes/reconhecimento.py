from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import BadRequestError
from app.database.session import get_db
from app.models.models import Usuario
from app.routes.auth import get_current_user
from app.schemas.schemas import ReconhecimentoFacialResponse
from app.services.face_recognition_service import FaceImagePayload
from app.services.reconhecimento_service import ReconhecimentoFacialWorkflow

router = APIRouter()


def get_reconhecimento_workflow(db: Session = Depends(get_db)) -> ReconhecimentoFacialWorkflow:
    return ReconhecimentoFacialWorkflow(db)


def _validar_tamanho_bytes(content: bytes) -> None:
    if len(content) > settings.MAX_IMAGE_UPLOAD_BYTES:
        raise BadRequestError("Imagem muito grande. Maximo 5MB.")


def _validar_tamanho_base64(base64_image: str) -> None:
    limite_base64 = ((settings.MAX_IMAGE_UPLOAD_BYTES + 2) // 3) * 4 + 128
    if len(base64_image.encode("utf-8")) > limite_base64:
        raise BadRequestError("Imagem muito grande. Maximo 5MB.")


async def _extrair_payload_imagem(request: Request) -> FaceImagePayload:
    content_type = request.headers.get("content-type", "")

    if "multipart/form-data" in content_type:
        form = await request.form()
        upload = form.get("imagem") or form.get("file")
        if upload is not None and hasattr(upload, "read"):
            content = await upload.read()
            if not content:
                raise BadRequestError("Imagem nao fornecida")
            _validar_tamanho_bytes(content)
            return FaceImagePayload(
                content=content,
                filename=getattr(upload, "filename", None),
                content_type=getattr(upload, "content_type", None),
            )

        imagem_base64 = form.get("imagem_base64") or form.get("base64")
        if imagem_base64:
            imagem_base64 = str(imagem_base64)
            _validar_tamanho_base64(imagem_base64)
            return FaceImagePayload(base64_image=imagem_base64)

    if "application/json" in content_type:
        try:
            body = await request.json()
        except ValueError as exc:
            raise BadRequestError("JSON invalido") from exc
        imagem_base64 = body.get("imagem_base64") or body.get("base64") or body.get("image")
        if imagem_base64:
            imagem_base64 = str(imagem_base64)
            _validar_tamanho_base64(imagem_base64)
            return FaceImagePayload(base64_image=imagem_base64)

    if content_type.startswith("image/"):
        content = await request.body()
        if content:
            _validar_tamanho_bytes(content)
            return FaceImagePayload(content=content, filename="imagem", content_type=content_type)

    raise BadRequestError("Imagem nao fornecida")


@router.post("/facial", response_model=ReconhecimentoFacialResponse)
async def reconhecer_facial(
    request: Request,
    user: Usuario = Depends(get_current_user),
    workflow: ReconhecimentoFacialWorkflow = Depends(get_reconhecimento_workflow),
):
    payload = await _extrair_payload_imagem(request)
    resultado, presenca = await workflow.processar(payload, user)
    return {
        "aluno_id": resultado.aluno_id,
        "confianca": resultado.confianca,
        "presenca": presenca,
        "mensagem": "Presenca registrada por reconhecimento facial",
    }
