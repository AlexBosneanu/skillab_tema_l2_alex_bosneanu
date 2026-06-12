"""pipeline.py — load → chunk → extract → store

Utilizare:
    python pipeline.py <cale_fisier>
    python pipeline.py docs/contract.pdf
    python pipeline.py demo/contract_demo.txt
"""
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_text_splitters import RecursiveCharacterTextSplitter

from db.database import transaction
from db.repository import DocumentRepository, ChunkRepository
from loaders.registry import load
from rag.service import RAGService
from schemas.extraction import DocumentExtraction, ExtractionResult

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

_splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)

_EXTRACTION_PROMPT = """\
Extrage informații structurate din documentul de mai jos.
Identifică tipul documentului (invoice/contract/report/letter/other)
și metadate cheie relevante (număr document, date, părți implicate, sume etc.).

Filename: {filename}
Content:
{content}
"""


def _get_llm() -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0)


def process(file: Path) -> ExtractionResult:
    file = Path(file)
    logger.info("=== Procesare: %s ===", file.name)

    # 1. Load — registry pe extensie (PDF / DOCX / TXT)
    try:
        content = load(file)
        logger.info("Încărcat: %d caractere", len(content))
    except Exception as e:
        return ExtractionResult(success=False, error=f"load failed: {e}")

    # 2. Chunk (800 chars, 100 overlap — specificat în temă)
    chunks = _splitter.split_text(content)
    logger.info("Chunking: %d bucăți", len(chunks))

    # 3. Extract structured data via LLM (llm.with_structured_output)
    try:
        prompt = _EXTRACTION_PROMPT.format(filename=file.name, content=content[:4000])
        llm = _get_llm().with_structured_output(DocumentExtraction)
        extraction: DocumentExtraction = llm.invoke(prompt)
        extraction.filename = file.name
        extraction.content = content  # full content, nu trunchierea din prompt
        logger.info("Extras: doc_type=%s", extraction.doc_type)
    except Exception as e:
        logger.warning("LLM extraction failed (%s) — salvăm cu doc_type=other", e)
        extraction = DocumentExtraction(filename=file.name, content=content, doc_type="other")

    # 4. Embed chunks cu sentence-transformers (paraphrase-multilingual-MiniLM-L12-v2)
    logger.info("Embeddings pentru %d chunks...", len(chunks))
    embeddings = RAGService.get_model().encode(chunks, convert_to_numpy=True)

    # 5. Store — Document + DocumentChunks atomic, idempotent pe filename
    try:
        with transaction() as db:
            doc_repo = DocumentRepository(db)
            existing = doc_repo.get_by_filename(file.name)
            if existing is not None:
                logger.info("Skip duplicat: %s (id=%d)", file.name, existing.id)
                return ExtractionResult(success=True, document=extraction)

            doc = doc_repo.create(**extraction.to_db_format())
            ChunkRepository(db).create_chunks_batch([
                {
                    "document_id": doc.id,
                    "content": chunk,
                    "chunk_index": i,
                    "embedding": emb.tolist(),
                }
                for i, (chunk, emb) in enumerate(zip(chunks, embeddings))
            ])
            logger.info("Salvat: id=%d, %d chunks", doc.id, len(chunks))
    except Exception as e:
        return ExtractionResult(success=False, error=f"store failed: {e}")

    return ExtractionResult(success=True, document=extraction)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python pipeline.py <cale_fisier>")
        print("  Ex: python pipeline.py demo/contract_demo.txt")
        sys.exit(1)

    result = process(Path(sys.argv[1]))
    if result.success:
        doc = result.document
        print(f"\n✓ Document procesat cu succes: {doc.filename}")
        print(f"  Tip: {doc.doc_type}")
        if doc.extra_metadata:
            for k, v in doc.extra_metadata.items():
                print(f"  {k}: {v}")
    else:
        print(f"\n✗ Eroare: {result.error}")
        sys.exit(1)
