from sqlalchemy.orm import Session

from app.models.models import FaceEmbedding, Presenca, Responsavel


class PresencaRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, presenca: Presenca) -> Presenca:
        self.db.add(presenca)
        return presenca

    def list_by_aluno(self, aluno_id: int) -> list[Presenca]:
        return (
            self.db.query(Presenca)
            .filter(Presenca.aluno_id == aluno_id)
            .order_by(Presenca.timestamp.desc())
            .all()
        )


class ResponsavelRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, responsavel: Responsavel) -> Responsavel:
        self.db.add(responsavel)
        return responsavel


class FaceEmbeddingRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, face_embedding: FaceEmbedding) -> FaceEmbedding:
        self.db.add(face_embedding)
        return face_embedding

    def list_by_aluno(self, aluno_id: int) -> list[FaceEmbedding]:
        return self.db.query(FaceEmbedding).filter(FaceEmbedding.aluno_id == aluno_id).all()
