from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import joinedload, Session

from db.models import Document, DocumentChunk


class DocumentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, filename: str, content: str, metadata: dict[str, Any]) -> Document:
        doc = Document(filename=filename, content=content, doc_metadata=metadata)
        self.db.add(doc)
        self.db.flush()    # generează id fără commit — tranzacția rămâne deschisă
        self.db.refresh(doc)
        return doc

    def get_by_id(self, doc_id: int) -> Document | None:
        return self.db.get(Document, doc_id)

    def get_by_filename(self, filename: str) -> Document | None:
        return self.db.execute(
            select(Document).where(Document.filename == filename)
        ).scalar_one_or_none()

    def get_all(self, skip: int = 0, limit: int = 100) -> list[Document]:
        return list(
            self.db.execute(
                select(Document).offset(skip).limit(limit)
            ).scalars().all()
        )


class ChunkRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_chunks_batch(self, chunks: list[dict]) -> list[DocumentChunk]:
        objs = [DocumentChunk(**c) for c in chunks]
        self.db.add_all(objs)
        self.db.flush()
        return objs

    def similarity_search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
    ) -> list[tuple[DocumentChunk, float]]:
        # 1 - cosine_distance → similaritate în [0, 1] (1 = identic)
        similarity = (
            1 - DocumentChunk.embedding.cosine_distance(query_embedding)
        ).label("score")

        stmt = (
            select(DocumentChunk, similarity)
            .options(joinedload(DocumentChunk.document))  # evită N+1 queries
            .order_by(DocumentChunk.embedding.cosine_distance(query_embedding))
            .limit(top_k)
        )

        rows = self.db.execute(stmt).all()
        return [(chunk, float(score)) for chunk, score in rows]
