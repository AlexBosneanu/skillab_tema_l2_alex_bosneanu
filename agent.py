"""Agent QA de tip ReAct, conectat la Gemini prin LangChain.

Pune cap la cap cele 4 componente ale temei:
  - tools/   -> ToolWrapper.catalog() (CE poate face) + ToolWrapper.call() (execuția)
  - prompts/ -> system prompt-ul "planner" (CUM se comportă agentul)
  - LLM      -> Gemini (gemini-2.5-flash) prin langchain-google-genai
  - bucla ReAct -> Think (invoke) -> Act (tool_calls) -> Observe (ToolMessage) -> repeat

Rulează din folderul `proiect/`:  python agent.py "întrebarea ta"
"""

import os
import sys

# Pe Windows consola e adesea cp1252 și ar crăpa la diacritice ('ă', 'î'...).
# Forțăm stdout pe UTF-8 ca răspunsurile în română să se afișeze corect.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_google_genai import ChatGoogleGenerativeAI

from prompts.registry import get_prompt_registry
from tools import ToolWrapper

# Citește variabilele din .env (GOOGLE_API_KEY etc.) în os.environ.
load_dotenv()

MODEL = "gemini-2.5-flash"
MAX_ITERATIONS = 6


def build_llm():
    """Creează clientul Gemini și îi atașează catalogul de tool-uri (bind_tools)."""
    key = os.getenv("GOOGLE_API_KEY", "").strip()
    if not key or key == "your_google_api_key_here":
        raise RuntimeError(
            "Lipsește GOOGLE_API_KEY. Ia o cheie gratuită de pe "
            "https://aistudio.google.com/apikey și pune-o în fișierul .env."
        )
    llm = ChatGoogleGenerativeAI(model=MODEL, temperature=0.2)
    # bind_tools: îi spunem modelului ce tool-uri are la dispoziție (catalog = JSON Schema).
    # Modelul nu execută nimic — doar poate cere apelarea unui tool.
    return llm.bind_tools(ToolWrapper.catalog())


def _text_raspuns(raspuns: AIMessage) -> str:
    """Extrage textul curat din răspuns.

    În langchain-core 1.x, `.content` poate fi un string SAU o listă de
    „content blocks" (dict-uri cu cheia 'text'). Tratăm ambele cazuri.
    """
    content = raspuns.content
    if isinstance(content, str):
        return content
    parti = [
        bloc.get("text", "") if isinstance(bloc, dict) else str(bloc)
        for bloc in content
    ]
    return "".join(parti).strip()


def react_loop(
    llm_with_tools,
    mesaje: list,
    max_iterations: int = MAX_ITERATIONS,
    verbose: bool = True,
) -> str:
    """Bucla Think -> Act -> Observe -> Repeat (adaptată din slide 47).

    `max_iterations` e plasa de siguranță: fără ea, un model care tot cere tool-uri
    ar bucla la infinit (costuri necontrolate, timeout-uri în producție).
    """
    for i in range(1, max_iterations + 1):
        # THINK: modelul decide — răspunde direct sau cere unul/mai multe tool-uri.
        raspuns: AIMessage = llm_with_tools.invoke(mesaje)
        mesaje.append(raspuns)

        # Dacă NU mai cere tool-uri -> avem răspunsul final.
        if not raspuns.tool_calls:
            if verbose:
                print(f"[iter {i}] THINK -> răspuns final")
            return _text_raspuns(raspuns)

        if verbose:
            print(f"[iter {i}] THINK -> cere {len(raspuns.tool_calls)} tool(uri)")

        # ACT: executăm TOATE tool-urile cerute în acest tur
        # (suport pentru "multiple tool calls în același turn").
        for tool_call in raspuns.tool_calls:
            nume = tool_call["name"]
            args = tool_call["args"]
            rezultat = ToolWrapper.call(nume, args)  # validare + execuție sigură
            if verbose:
                print(f"[iter {i}] ACT  -> {nume}({args})")
                print(f"[iter {i}] OBS  <- {rezultat}")
            # OBSERVE: trimitem rezultatul înapoi modelului, legat prin tool_call_id.
            # tool_call_id LEAGĂ cererea de rezultat (critic la apeluri multiple).
            mesaje.append(
                ToolMessage(content=str(rezultat), tool_call_id=tool_call["id"])
            )

    # S-au epuizat iterațiile fără răspuns final — răspuns parțial, nu crash.
    return (
        "Nu am ajuns la un răspuns final în limita de iterații. "
        "Reformulează întrebarea sau crește max_iterations."
    )


def ask(intrebare: str, verbose: bool = True) -> str:
    """Răspunde la o întrebare folosind agentul ReAct + tool-uri."""
    llm_with_tools = build_llm()

    # System prompt-ul vine din prompts/planner.yaml, randat cu Jinja2 (variabile dinamice).
    system = get_prompt_registry().render(
        "planner",
        rol="un asistent QA precis",
        domeniu="calcule, dată/oră și căutare web",
        max_cuvinte=200,
    )
    mesaje = [SystemMessage(content=system), HumanMessage(content=intrebare)]
    return react_loop(llm_with_tools, mesaje, verbose=verbose)


if __name__ == "__main__":
    # Input real de test: îl iei din linia de comandă, sau folosim exemplul de TVA din curs.
    intrebare = " ".join(sys.argv[1:]) or (
        "Vreau costul total cu TVA: Laptop 4500, Mouse 150, "
        "Tastatură 280 RON. TVA 19%."
    )
    print(f"\n=== Întrebare ===\n{intrebare}\n")
    print("=== Pași ReAct ===")
    raspuns = ask(intrebare)
    print("\n=== Răspuns final ===")
    print(raspuns)
