import logging

from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, ForbiddenError, NotFoundError
from app.core.security import hash_senha
from app.models.models import Usuario
from app.repositories.aluno_repository import AlunoRepository
from app.repositories.usuario_repository import UsuarioRepository
from app.schemas.schemas import AtualizarUsuarioRequest, RedefinirSenhaRequest
from app.services.aluno_service import AlunoService
from app.services.media import deletar_foto_cloudinary

logger = logging.getLogger(__name__)


class AdminService:
    def __init__(self, db: Session):
        self.db = db
        self.usuarios = UsuarioRepository(db)
        self.alunos = AlunoRepository(db)
        self.aluno_service = AlunoService(db)

    def estatisticas(self) -> dict:
        total_usuarios = self.usuarios.count_all()
        usuarios_ativos = self.usuarios.count_active()
        return {
            "total_usuarios": total_usuarios,
            "usuarios_ativos": usuarios_ativos,
            "usuarios_inativos": total_usuarios - usuarios_ativos,
            "total_alunos": self.alunos.count_all(),
        }

    def listar_usuarios(self) -> list[dict]:
        return [
            {
                "id": u.id,
                "nome": u.nome,
                "email": u.email,
                "ativo": u.ativo,
                "is_superuser": u.is_superuser,
                "criado_em": u.criado_em,
                "total_alunos": self.alunos.count_by_user(u.id),
            }
            for u in self.usuarios.list_all()
        ]

    def atualizar_usuario(
        self,
        usuario_id: int,
        body: AtualizarUsuarioRequest,
        admin: Usuario,
    ) -> dict:
        usuario = self._buscar_usuario(usuario_id)
        if usuario.is_superuser and usuario.id != admin.id:
            raise ForbiddenError("Nao e possivel editar outro superusuario")
        if body.nome is not None:
            usuario.nome = body.nome
        if body.email is not None:
            if self.usuarios.email_exists_for_other_user(body.email, usuario_id):
                raise BadRequestError("E-mail ja esta em uso")
            usuario.email = body.email
        if body.ativo is not None:
            usuario.ativo = body.ativo
        self.db.commit()
        logger.info("Usuario id=%d atualizado pelo admin id=%d", usuario_id, admin.id)
        return {"id": usuario.id, "nome": usuario.nome, "email": usuario.email, "ativo": usuario.ativo}

    def redefinir_senha(
        self,
        usuario_id: int,
        body: RedefinirSenhaRequest,
        admin: Usuario,
    ) -> dict:
        if len(body.nova_senha) < 6:
            raise BadRequestError("Senha deve ter no minimo 6 caracteres")
        usuario = self._buscar_usuario(usuario_id)
        if usuario.is_superuser and usuario.id != admin.id:
            raise ForbiddenError("Nao e possivel redefinir senha de outro superusuario")
        usuario.senha = hash_senha(body.nova_senha)
        self.db.commit()
        logger.info("Senha do usuario id=%d redefinida pelo admin id=%d", usuario_id, admin.id)
        return {"mensagem": "Senha redefinida com sucesso"}

    def toggle_usuario_ativo(self, usuario_id: int, admin: Usuario) -> dict:
        usuario = self._buscar_usuario(usuario_id)
        if usuario.is_superuser:
            raise ForbiddenError("Nao e possivel desativar um superusuario")
        usuario.ativo = not usuario.ativo
        self.db.commit()
        status_str = "ativado" if usuario.ativo else "desativado"
        logger.info("Usuario id=%d %s pelo admin id=%d", usuario_id, status_str, admin.id)
        return {"id": usuario.id, "ativo": usuario.ativo, "mensagem": f"Usuario {status_str}"}

    def deletar_usuario(self, usuario_id: int, admin: Usuario) -> dict:
        usuario = self._buscar_usuario(usuario_id)
        if usuario.is_superuser:
            raise ForbiddenError("Nao e possivel remover um superusuario")

        alunos_do_usuario = self.alunos.list_by_user(usuario_id)
        for aluno in alunos_do_usuario:
            deletar_foto_cloudinary(aluno.foto)

        self.usuarios.delete(usuario)
        self.db.commit()
        logger.info("Usuario id=%d deletado pelo admin id=%d", usuario_id, admin.id)
        return {"mensagem": "Usuario removido com sucesso"}

    def listar_todos_alunos(self, page: int = 1, limit: int = 50) -> dict:
        """Lista todos os alunos com paginação.
        
        Args:
            page: Número da página (começa em 1)
            limit: Número de registros por página
            
        Returns:
            Dicionário com dados paginados e metadados
        """
        skip = (page - 1) * limit
        alunos, total = self.alunos.list_all_with_usuario(skip=skip, limit=limit)
        
        return {
            "data": [
                {
                    "id": a[0].id,
                    "nome": a[0].nome,
                    "numero_inscricao": a[0].numero_inscricao,
                    "telefone": a[0].telefone,
                    "foto": a[0].foto,
                    "criado_em": a[0].criado_em,
                    "user_id": a[0].user_id,
                    "usuario_nome": a[1],
                    "usuario_email": a[2],
                }
                for a in alunos
            ],
            "paginacao": {
                "total": total,
                "pagina": page,
                "limite": limit,
                "paginas_totais": (total + limit - 1) // limit,
                "proxima_pagina": page + 1 if page * limit < total else None,
            },
        }

    def deletar_aluno(self, aluno_id: int, admin: Usuario) -> dict:
        self.aluno_service.deletar_admin(admin, aluno_id)
        return {"mensagem": "Aluno removido com sucesso"}

    def _buscar_usuario(self, usuario_id: int) -> Usuario:
        usuario = self.usuarios.get_by_id(usuario_id)
        if not usuario:
            raise NotFoundError("Usuario nao encontrado")
        return usuario
