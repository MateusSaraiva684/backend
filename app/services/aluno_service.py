import logging

from fastapi import UploadFile
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

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
        page: int = 1,
        limit: int = 50,
    ) -> dict:
        """Lista alunos com paginação.
        
        Args:
            user: Usuário autenticado
            turma: Filtrar por turma (opcional)
            busca: Buscar por nome ou número (opcional)
            page: Número da página (começa em 1)
            limit: Itens por página
            
        Returns:
            Dict com dados paginados
        """
        # Validar page e limit
        if page < 1:
            page = 1
        if limit < 1 or limit > 100:
            limit = 50
            
        skip = (page - 1) * limit
        alunos, total = self.alunos.list_by_user(
            user.id, 
            turma=turma, 
            busca=busca, 
            skip=skip, 
            limit=limit
        )
        
        total_pages = (total + limit - 1) // limit  # Ceiling division
        
        # Converter objetos Aluno para dicionários serializáveis
        dados_alunos = []
        for aluno in alunos:
            dados_alunos.append({
                "id": aluno.id,
                "nome": aluno.nome,
                "numero_inscricao": aluno.numero_inscricao,
                "telefone": aluno.telefone,
                "turma": aluno.turma,
                "foto": aluno.foto,
                "criado_em": aluno.criado_em,
                "user_id": aluno.user_id,
                "responsaveis": [
                    {"id": r.id, "nome": r.nome, "telefone": r.telefone}
                    for r in aluno.responsaveis
                ] if hasattr(aluno, 'responsaveis') else []
            })
        
        return {
            "data": dados_alunos,
            "paginacao": {
                "total": total,
                "pagina": page,
                "limite": limit,
                "paginas_totais": total_pages,
                "proxima_pagina": page + 1 if skip + limit < total else None,
            }
        }

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
        
        try:
            foto_url = salvar_foto(foto) if foto else None
        except Exception as e:
            logger.error("Erro ao fazer upload de foto: %s", str(e))
            raise
        
        aluno = Aluno(
            nome=nome,
            numero_inscricao=numero_inscricao,
            telefone=telefone,
            turma=turma.strip() or None,
            foto=foto_url,
            user_id=user.id,
        )
        try:
            self.alunos.add(aluno)
            self.db.flush()  # Força constraint check do UNIQUE
            self.db.commit()
            self.db.refresh(aluno)
            logger.info("Aluno criado: id=%d por usuario id=%d", aluno.id, user.id)
            return aluno
        except IntegrityError as e:
            self.db.rollback()
            # Detecta violação de constraint UNIQUE (SQLite, PostgreSQL)
            if "alunos.user_id, alunos.numero_inscricao" in str(e) or "uq_alunos_user_numero_inscricao" in str(e):
                logger.warning("Numero inscricao duplicado para usuario id=%d: %s", user.id, numero_inscricao)
                raise BadRequestError("Numero de inscricao ja cadastrado para esta escola")
            logger.error("Erro ao criar aluno (integridade): %s", str(e))
            raise BadRequestError("Erro ao criar aluno: dados inválidos")
        except Exception as e:
            self.db.rollback()
            logger.error("Erro ao criar aluno: %s", str(e))
            raise

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

        aluno.nome = nome
        aluno.numero_inscricao = numero_inscricao
        aluno.telefone = telefone
        aluno.turma = turma.strip() or None

        nova_url = salvar_foto(foto)
        if nova_url:
            deletar_foto_cloudinary(aluno.foto)
            aluno.foto = nova_url

        try:
            self.db.flush()  # Força constraint check do UNIQUE
            self.db.commit()
            self.db.refresh(aluno)
            logger.info("Aluno atualizado: id=%d", aluno_id)
            return aluno
        except IntegrityError as e:
            self.db.rollback()
            # Detecta violação de constraint UNIQUE (SQLite, PostgreSQL)
            if "alunos.user_id, alunos.numero_inscricao" in str(e) or "uq_alunos_user_numero_inscricao" in str(e):
                logger.warning("Numero inscricao duplicado na atualização: %s", numero_inscricao)
                raise BadRequestError("Numero de inscricao ja cadastrado para esta escola")
            logger.error("Erro ao atualizar aluno (integridade): %s", str(e))
            raise BadRequestError("Erro ao atualizar aluno: dados inválidos")
        except Exception as e:
            self.db.rollback()
            logger.error("Erro ao atualizar aluno: %s", str(e))
            raise

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
