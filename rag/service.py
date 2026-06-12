import logging

from sentence_transformers import SentenceTransformer
from sqlalchemy.orm import Session

from db.models import DocumentChunk
from db.repository import ChunkRepository

logger = logging.getLogger(__name__)

# Model recomandat în curs (slide44.py) — multilingual, 384-dim, bun pentru română
MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
DEFAULT_THRESHOLD = 0.2


class RAGService:
    _model: SentenceTransformer | None = None  # singleton per proces (~80MB RAM)

    def __init__(self, db: Session) -> None:
        self.repo = ChunkRepository(db)

    @classmethod
    def get_model(cls) -> SentenceTransformer:
        if cls._model is None:
            logger.info("Încărcare model sentence-transformers: %s (prima oară)", MODEL_NAME)
            cls._model = SentenceTransformer(MODEL_NAME)
        return cls._model

    def search(
        self,
        query: str,
        top_k: int = 5,
    ) -> list[tuple[DocumentChunk, float]]:
        q_emb = self.get_model().encode(query, convert_to_numpy=True).tolist()
        return self.repo.similarity_search(q_emb, top_k=top_k)

    def get_context(
        self,
        query: str,
        top_k: int = 5,
        threshold: float = DEFAULT_THRESHOLD,
    ) -> str:
        results = self.search(query, top_k=top_k)
        relevant = [(chunk, score) for chunk, score in results if score >= threshold]
        if not relevant:
            return ""
        parts = [
            f"[{chunk.document.filename} | chunk {chunk.chunk_index} | score {score:.2f}]\n"
            f"{chunk.content}"
            for chunk, score in relevant
        ]
        return "\n\n".join(parts)
