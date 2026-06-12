import logging
from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader, TextLoader

logger = logging.getLogger(__name__)

LOADERS = {
    ".pdf": PyPDFLoader,
    ".docx": Docx2txtLoader,
    ".txt": TextLoader,
}


def load(path: Path) -> str:
    path = Path(path)
    loader_cls = LOADERS.get(path.suffix.lower())
    if loader_cls is None:
        raise ValueError(
            f"Format nesuportat: '{path.suffix}'. Formate suportate: {list(LOADERS)}"
        )
    try:
        if path.suffix.lower() == ".txt":
            loader = loader_cls(str(path), autodetect_encoding=True)
        else:
            loader = loader_cls(str(path))
        docs = loader.load()
        return "\n\n".join(d.page_content for d in docs if d.page_content.strip())
    except Exception as e:
        logger.error("Eroare la încărcarea %s: %s", path.name, e)
        raise
