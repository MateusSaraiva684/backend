from sqlalchemy.orm import Session

from app.models.models import Aluno, Usuario


class AlunoRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_by_user(
        self,
        user_id: int,
        turma: str | None = None,
        busca: str | None = None,
    ) -> list[Aluno]:
        query = self.db.query(Aluno).filter(Aluno.user_id == user_id)
        if turma:
            query = query.filter(Aluno.turma == turma)
        if busca:
            termo = f"%{busca.strip()}%"
            query = query.filter(Aluno.nome.ilike(termo) | Aluno.numero_inscricao.ilike(termo))
        return query.order_by(Aluno.nome).all()

    def list_all_with_usuario(self):
        return (
            self.db.query(Aluno, Usuario.nome.label("usuario_nome"), Usuario.email.label("usuario_email"))
            .join(Usuario, Aluno.user_id == Usuario.id)
            .order_by(Aluno.id.desc())
            .all()
        )

    def list_turmas_by_user(self, user_id: int) -> list[str]:
        resultado = (
            self.db.query(Aluno.turma)
            .filter(Aluno.user_id == user_id, Aluno.turma.isnot(None), Aluno.turma != "")
            .distinct()
            .order_by(Aluno.turma)
            .all()
        )
        return [r.turma for r in resultado]

    def get(self, aluno_id: int) -> Aluno | None:
        return self.db.query(Aluno).filter(Aluno.id == aluno_id).first()

    def get_by_user(self, aluno_id: int, user_id: int) -> Aluno | None:
        return self.db.query(Aluno).filter(Aluno.id == aluno_id, Aluno.user_id == user_id).first()

    def count_all(self) -> int:
        return self.db.query(Aluno).count()

    def count_by_user(self, user_id: int) -> int:
        return self.db.query(Aluno).filter(Aluno.user_id == user_id).count()

    def numero_inscricao_exists(
        self,
        user_id: int,
        numero_inscricao: str,
        aluno_id: int | None = None,
    ) -> bool:
        query = self.db.query(Aluno).filter(
            Aluno.user_id == user_id,
            Aluno.numero_inscricao == numero_inscricao,
        )
        if aluno_id is not None:
            query = query.filter(Aluno.id != aluno_id)
        return query.first() is not None

    def add(self, aluno: Aluno) -> Aluno:
        self.db.add(aluno)
        return aluno

    def delete(self, aluno: Aluno) -> None:
        self.db.delete(aluno)
