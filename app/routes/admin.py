import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.security import hash_senha
from app.database.session import get_db
from app.models.models import Usuario, Aluno
from app.routes.auth import get_current_user
from app.services.media import deletar_foto_cloudinary

router = APIRouter()
logger = logging.getLogger(__name__)


def get_superuser(user: Usuario = Depends(get_current_user)) -> Usuario:
    if not user.is_superuser:
        raise HTTPException(status_code=403, detail="Acesso restrito a administradores")
    return user


@router.get("/stats")
def estatisticas(
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_superuser),
):
    total_usuarios = db.query(Usuario).count()
    usuarios_ativos = db.query(Usuario).filter(Usuario.ativo == True).count()
    total_alunos = db.query(Aluno).count()
    return {
        "total_usuarios": total_usuarios,
        "usuarios_ativos": usuarios_ativos,
        "usuarios_inativos": total_usuarios - usuarios_ativos,
        "total_alunos": total_alunos,
    }


@router.get("/usuarios")
def listar_usuarios(
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_superuser),
):
    usuarios = db.query(Usuario).order_by(Usuario.id.desc()).all()
    return [
        {
            "id": u.id,
            "nome": u.nome,
            "email": u.email,
            "ativo": u.ativo,
            "is_superuser": u.is_superuser,
            "criado_em": u.criado_em,
            "total_alunos": db.query(Aluno).filter(Aluno.user_id == u.id).count(),
        }
        for u in usuarios
    ]


class AtualizarUsuarioRequest(BaseModel):
    nome: Optional[str] = None
    email: Optional[str] = None
    ativo: Optional[bool] = None


@router.patch("/usuarios/{usuario_id}")
def atualizar_usuario(
    usuario_id: int,
    body: AtualizarUsuarioRequest,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(get_superuser),
):
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario nao encontrado")
    if usuario.is_superuser and usuario.id != admin.id:
        raise HTTPException(status_code=403, detail="Nao e possivel editar outro superusuario")
    if body.nome is not None:
        usuario.nome = body.nome
    if body.email is not None:
        existente = db.query(Usuario).filter(
            Usuario.email == body.email, Usuario.id != usuario_id
        ).first()
        if existente:
            raise HTTPException(status_code=400, detail="E-mail ja esta em uso")
        usuario.email = body.email
    if body.ativo is not None:
        usuario.ativo = body.ativo
    db.commit()
    logger.info("Usuario id=%d atualizado pelo admin id=%d", usuario_id, admin.id)
    return {"id": usuario.id, "nome": usuario.nome, "email": usuario.email, "ativo": usuario.ativo}


class RedefinirSenhaRequest(BaseModel):
    nova_senha: str


@router.patch("/usuarios/{usuario_id}/senha")
def redefinir_senha(
    usuario_id: int,
    body: RedefinirSenhaRequest,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(get_superuser),
):
    if len(body.nova_senha) < 6:
        raise HTTPException(status_code=400, detail="Senha deve ter no minimo 6 caracteres")
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario nao encontrado")
    if usuario.is_superuser and usuario.id != admin.id:
        raise HTTPException(status_code=403, detail="Nao e possivel redefinir senha de outro superusuario")
    usuario.senha = hash_senha(body.nova_senha)
    db.commit()
    logger.info("Senha do usuario id=%d redefinida pelo admin id=%d", usuario_id, admin.id)
    return {"mensagem": "Senha redefinida com sucesso"}


@router.patch("/usuarios/{usuario_id}/ativo")
def toggle_usuario_ativo(
    usuario_id: int,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(get_superuser),
):
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario nao encontrado")
    if usuario.is_superuser:
        raise HTTPException(status_code=403, detail="Nao e possivel desativar um superusuario")
    usuario.ativo = not usuario.ativo
    db.commit()
    status_str = "ativado" if usuario.ativo else "desativado"
    logger.info("Usuario id=%d %s pelo admin id=%d", usuario_id, status_str, admin.id)
    return {"id": usuario.id, "ativo": usuario.ativo, "mensagem": f"Usuario {status_str}"}


@router.delete("/usuarios/{usuario_id}")
def deletar_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(get_superuser),
):
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario nao encontrado")
    if usuario.is_superuser:
        raise HTTPException(status_code=403, detail="Nao e possivel remover um superusuario")

    alunos_do_usuario = db.query(Aluno).filter(Aluno.user_id == usuario_id).all()
    for aluno in alunos_do_usuario:
        deletar_foto_cloudinary(aluno.foto)

    db.delete(usuario)
    db.commit()
    logger.info("Usuario id=%d deletado pelo admin id=%d", usuario_id, admin.id)
    return {"mensagem": "Usuario removido com sucesso"}


@router.get("/alunos")
def listar_todos_alunos(
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_superuser),
):
    alunos = (
        db.query(Aluno, Usuario.nome.label("usuario_nome"), Usuario.email.label("usuario_email"))
        .join(Usuario, Aluno.user_id == Usuario.id)
        .order_by(Aluno.id.desc())
        .all()
    )
    return [
        {
            "id": a.Aluno.id,
            "nome": a.Aluno.nome,
            "numero_inscricao": a.Aluno.numero_inscricao,
            "telefone": a.Aluno.telefone,
            "foto": a.Aluno.foto,
            "criado_em": a.Aluno.criado_em,
            "user_id": a.Aluno.user_id,
            "usuario_nome": a.usuario_nome,
            "usuario_email": a.usuario_email,
        }
        for a in alunos
    ]


@router.delete("/alunos/{aluno_id}")
def deletar_aluno(
    aluno_id: int,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(get_superuser),
):
    aluno = db.query(Aluno).filter(Aluno.id == aluno_id).first()
    if not aluno:
        raise HTTPException(status_code=404, detail="Aluno nao encontrado")

    deletar_foto_cloudinary(aluno.foto)
    db.delete(aluno)
    db.commit()
    logger.info("Aluno id=%d deletado pelo admin id=%d", aluno_id, admin.id)
    return {"mensagem": "Aluno removido com sucesso"}
