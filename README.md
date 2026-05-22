# Tema L2 — Agent QA cu Tools + Prompts (ReAct)

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
```

Vei vedea pașii ReAct (THINK / ACT / OBS) și apoi răspunsul final.

## Exemplu

Întrebare: *„Vreau costul total cu TVA: Laptop 4500, Mouse 150, Tastatură 280 RON. TVA 19%."*
Agentul apelează `calculator` pentru subtotal, TVA și total, apoi răspunde cu cifrele finale.
