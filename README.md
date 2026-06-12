# Tema L2+L4 — Agent QA cu Tools, Prompts (ReAct) + Document Analyst cu RAG

Agent de tip **ReAct** care răspunde la întrebări folosind **tool-uri** (calculator,
dată/oră, căutare web) definite cu **Pydantic** și **prompturi** stocate în **YAML + Jinja2**.
Furnizor LLM: **Google Gemini** (`gemini-2.5-flash`) prin LangChain.

## Diagramă (flux de apeluri)

Fluxul complet — de la `python agent.py` până la răspunsul de la Gemini — e ilustrat în
**[`diagrama.html`](diagrama.html)**. E un fișier static (CSS inline, fără biblioteci),
deschide-l direct în browser. Arată cum se înlănțuie fișierele și funcțiile pe trei faze:
înregistrarea tool-urilor → pregătirea LLM-ului + prompturilor → bucla ReAct.

## Structură

```
proiect/
├── agent.py                # orchestrare LLM + bucla ReAct (Think → Act → Observe)
├── tools/
│   ├── __init__.py         # importă basic_tools (înregistrează) + exportă ToolWrapper
│   ├── registry.py         # TOOL_REGISTRY + decoratorul @register_tool
│   ├── params_models.py    # Pydantic BaseModel pentru parametrii fiecărui tool
│   ├── basic_tools.py      # calculator, get_datetime, web_search
│   └── tool_wrapper.py     # ToolWrapper.call() + ToolWrapper.catalog()
├── prompts/
│   ├── registry.py         # PromptRegistry (încarcă YAML + render Jinja2)
│   ├── planner.yaml        # system prompt principal al agentului
│   ├── analyst.yaml        # analiză de feedback (demo Jinja2)
│   ├── summary.yaml        # rezumare
│   └── extract.yaml        # extragere structurată
├── requirements.txt
├── .env.example
├── diagrama.html           # diagramă vizuală a fluxului de apeluri (deschide în browser)
└── README.md
```

## Cele 4 componente ale temei

1. **Tools cu Pydantic** — `params_models.py` (params), `@register_tool` + `TOOL_REGISTRY`
   (`registry.py`), `ToolWrapper.call()` + `ToolWrapper.catalog()` (`tool_wrapper.py`).
2. **Prompts cu YAML + Jinja2** — `prompts/*.yaml` încărcate de `PromptRegistry`, randate
   cu variabile dinamice Jinja2.
3. **Agent QA** — `agent.py` cheamă LLM-ul cu tool-uri + prompt și dă un răspuns final clar.
4. **ReAct Pattern** — bucla `react_loop()`: Think → Act → Observe → Repeat, cu
   `max_iterations`, error handling și mai multe tool-call-uri în același tur.

## Setup

```powershell
# din folderul proiect/
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# cheia Gemini (gratuită: https://aistudio.google.com/apikey)
copy .env.example .env
# editează .env și pune GOOGLE_API_KEY=...
```

## Rulare

```powershell
# exemplul implicit (calcul TVA)
python agent.py

# întrebare proprie
python agent.py "Ce dată și oră e acum în Tokyo?"

# cu RAG — după ce ai încărcat documente
python agent.py "Ce clauze de reziliere avem în documente?"
```

Vei vedea pașii ReAct (THINK / ACT / OBS) și apoi răspunsul final.

## Exemplu

Întrebare: *„Vreau costul total cu TVA: Laptop 4500, Mouse 150, Tastatură 280 RON. TVA 19%."*
Agentul apelează `calculator` pentru subtotal, TVA și total, apoi răspunde cu cifrele finale.

---

## Tema L4 — Document Analyst cu RAG

Extensie care adaugă un pipeline de procesare documente + căutare semantică.

### Componente adăugate

```
proiect/
├── docker-compose.yml          # PostgreSQL 16 + pgvector
├── alembic.ini                 # configurare migrări
├── pipeline.py                 # load → chunk → extract → store
├── db/
│   ├── database.py             # SQLAlchemy engine + transaction() context manager
│   ├── models.py               # Document + DocumentChunk (one-to-many, Vector(384))
│   ├── repository.py           # DocumentRepository + ChunkRepository
│   └── migrations/
│       └── versions/001_initial_schema.py  # CREATE EXTENSION vector + HNSW index
├── loaders/
│   └── registry.py             # loader registry: .pdf → PyPDFLoader, .docx, .txt
├── schemas/
│   └── extraction.py           # DocumentExtraction + ExtractionResult (Pydantic)
├── rag/
│   └── service.py              # RAGService — embeddings + cosine similarity search
├── tools/
│   └── rag_tool.py             # @register_tool search_documents
└── demo/
    └── contract_demo.txt       # document de test
```

### Setup RAG

```powershell
# 1. Pornire PostgreSQL cu pgvector
docker compose up -d

# 2. Instalare dependențe noi
pip install -r requirements.txt
# NOTĂ: sentence-transformers descarcă ~100MB la prima rulare

# 3. Adaugă DATABASE_URL în .env (copiază din .env.example)
copy .env.example .env
# editează .env: GOOGLE_API_KEY + DATABASE_URL

# 4. Creare tabele + HNSW index
alembic upgrade head

# 5. Procesare document de test
python pipeline.py demo/contract_demo.txt

# 6. Test agent cu RAG
python agent.py "Ce clauze de reziliere avem în documente?"
```

### Flow pipeline

```
process(file)
    ↓
load(file)          # loaders/registry.py — PyPDFLoader / Docx2txtLoader / TextLoader
    ↓
split_text(800, 100) # RecursiveCharacterTextSplitter — 800 chars, 100 overlap
    ↓
llm.with_structured_output(DocumentExtraction)  # extragere metadate via Gemini
    ↓
sentence_transformers.encode(chunks)  # paraphrase-multilingual-MiniLM-L12-v2 → 384-dim
    ↓
DocumentRepository.create() + ChunkRepository.create_chunks_batch()  # atomic via transaction()
```

### Flow RAG în agent

```
agent.invoke("Ce clauze de reziliere avem?")
    ↓
search_documents(query="clauze reziliere", top_k=3)
    ↓
RAGService.get_context() → similarity_search() cu cosine distance (HNSW index)
    ↓
context = "[contract_demo.txt | chunk 5 | score 0.82]\nClauza 7: reziliere cu preaviz 60 zile..."
    ↓
LLM răspunde cu context → "Conform contract_demo.txt, rezilierea se face cu preaviz de 60 zile..."
```
