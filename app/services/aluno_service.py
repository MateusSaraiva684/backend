import logging

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, NotFoundError
from app.models.models import Aluno, Usuario
from app.repositories.aluno_repository import AlunoRepository
from app.services.media import deletar_foto_cloudinary, salvar_foto

logger = logging.getLogger(__name__)


class AlunoService:
    def __init__(self, db: Session):
        self.db = db
        self.alunos = AlunoRepository(db)

    def listar_turmas(self, user: Usuario) -> list[str]:
        return self.alunos.list_turmas_by_user(user.id)

    def listar(
        self,
        user: Usuario,
        turma: str | None = None,
        busca: str | None = None,
    ) -> list[Aluno]:
        return self.alunos.list_by_user(user.id, turma=turma, busca=busca)

    def criar(
        self,
        user: Usuario,
        nome: str,
        numero_inscricao: str,
        telefone: str,
        turma: str = "",
        foto: UploadFile | None = None,
    ) -> Aluno:
        numero_inscricao = self._normalizar_numero_inscricao(numero_inscricao)
        self._garantir_numero_inscricao_disponivel(user.id, numero_inscricao)
        aluno = Aluno(
            nome=nome,
            numero_inscricao=numero_inscricao,
            telefone=telefone,
            turma=turma.strip() or None,
            foto=salvar_foto(foto),
            user_id=user.id,
        )
        self.alunos.add(aluno)
        self.db.commit()
        self.db.refresh(aluno)
        logger.info("Aluno criado: id=%d por usuario id=%d", aluno.id, user.id)
        return aluno

    def buscar(self, user: Usuario, aluno_id: int) -> Aluno:
        aluno = self.alunos.get_by_user(aluno_id, user.id)
        if not aluno:
            raise NotFoundError("Aluno nao encontrado")
        return aluno

    def buscar_para_usuario_ou_admin(self, user: Usuario, aluno_id: int) -> Aluno:
        aluno = self.alunos.get(aluno_id) if user.is_superuser else self.alunos.get_by_user(aluno_id, user.id)
        if not aluno:
            raise NotFoundError("Aluno nao encontrado")
        return aluno

    def atualizar(
        self,
        user: Usuario,
        aluno_id: int,
        nome: str,
        numero_inscricao: str,
        telefone: str,
        turma: str = "",
        foto: UploadFile | None = None,
    ) -> Aluno:
        aluno = self.buscar(user, aluno_id)
        numero_inscricao = self._normalizar_numero_inscricao(numero_inscricao)
        self._garantir_numero_inscricao_disponivel(
            user.id,
            numero_inscricao,
            aluno_id=aluno.id,
        )

        aluno.nome = nome
        aluno.numero_inscricao = numero_inscricao
        aluno.telefone = telefone
        aluno.turma = turma.strip() or None

        nova_url = salvar_foto(foto)
        if nova_url:
            deletar_foto_cloudinary(aluno.foto)
            aluno.foto = nova_url

        self.db.commit()
        self.db.refresh(aluno)
        logger.info("Aluno atualizado: id=%d", aluno_id)
        return aluno

    def deletar(self, user: Usuario, aluno_id: int) -> None:
        aluno = self.buscar(user, aluno_id)
        deletar_foto_cloudinary(aluno.foto)
        self.alunos.delete(aluno)
        self.db.commit()
        logger.info("Aluno deletado: id=%d por usuario id=%d", aluno_id, user.id)

    def deletar_admin(self, admin: Usuario, aluno_id: int) -> None:
        aluno = self.alunos.get(aluno_id)
        if not aluno:
            raise NotFoundError("Aluno nao encontrado")
        deletar_foto_cloudinary(aluno.foto)
        self.alunos.delete(aluno)
        self.db.commit()
        logger.info("Aluno id=%d deletado pelo admin id=%d", aluno_id, admin.id)

    def _normalizar_numero_inscricao(self, numero_inscricao: str) -> str:
        numero_inscricao = numero_inscricao.strip()
        if not numero_inscricao:
            raise BadRequestError("Numero de inscricao e obrigatorio")
        return numero_inscricao

    def _garantir_numero_inscricao_disponivel(
        self,
        user_id: int,
        numero_inscricao: str,
        aluno_id: int | None = None,
    ) -> None:
        if self.alunos.numero_inscricao_exists(user_id, numero_inscricao, aluno_id=aluno_id):
            raise BadRequestError("Numero de inscricao ja cadastrado para esta escola")
