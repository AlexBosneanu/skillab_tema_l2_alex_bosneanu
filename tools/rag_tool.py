import logging

from tools.registry import register_tool
from tools.params_models import SearchDocumentsParams

logger = logging.getLogger(__name__)


@register_tool
def search_documents(params: SearchDocumentsParams) -> str:
    """Caută informații relevante în documentele încărcate (facturi, contracte, rapoarte). Folosește când ești întrebat despre conținutul documentelor stocate în baza de date."""
    try:
        from db.database import transaction
        from rag.service import RAGService

        with transaction() as db:
            rag = RAGService(db)
            context = rag.get_context(params.query, top_k=params.top_k)
            if not context:
                return "Nu am găsit informații relevante în documentele stocate."
            return context
    except Exception as e:
        logger.warning("search_documents eroare: %s", e)
        return f"search_documents indisponibil: {e}"
