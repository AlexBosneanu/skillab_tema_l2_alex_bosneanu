"""Tool-urile de bază: calculator, get_datetime, web_search (slide 56-57).

Fiecare funcție:
  - primește UN singur argument de tip Pydantic BaseModel (params);
  - are docstring descriptiv — devine `description` pentru LLM și îi spune CE face,
    CÂND să-l folosească și CÂND nu;
  - e decorată cu @register_tool, care o înscrie automat în TOOL_REGISTRY la import.
"""

import ast
import operator
from datetime import datetime
from zoneinfo import ZoneInfo

from .params_models import CalculatorParams, GetDatetimeParams, WebSearchParams
from .registry import register_tool

# --- Calculator: evaluare SIGURĂ a expresiei (fără eval() brut) -------------

# eval() brut ar executa ORICE cod Python (ex: __import__('os').system(...)),
# deci e o gaură de securitate. În schimb parsăm expresia în AST și permitem
# DOAR operatori aritmetici dintr-o listă albă (whitelist).
_ALLOWED_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _safe_eval(node: ast.AST) -> float:
    """Evaluează recursiv un nod AST, acceptând doar numere și operatori din whitelist."""
    if isinstance(node, ast.Constant):  # un număr
        if isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
            return node.value
        raise ValueError(f"Valoare nepermisă: {node.value!r}")
    if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_OPERATORS:
        return _ALLOWED_OPERATORS[type(node.op)](
            _safe_eval(node.left), _safe_eval(node.right)
        )
    if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_OPERATORS:
        return _ALLOWED_OPERATORS[type(node.op)](_safe_eval(node.operand))
    raise ValueError("Expresie nepermisă (doar aritmetică simplă este acceptată).")


@register_tool
def calculator(params: CalculatorParams) -> str:
    """Evaluează o expresie matematică simplă (+, -, *, /, //, %, **).

    Folosește-l pentru calcule precise (sume, TVA, procente, conversii) — nu te baza
    pe aritmetica „din cap" a modelului. Exemple de input bun: '4500 + 150 + 280',
    '4930 * 0.19'.
    """
    tree = ast.parse(params.expression, mode="eval")
    rezultat = _safe_eval(tree.body)
    return str(rezultat)


# --- Data/ora curentă -------------------------------------------------------

@register_tool
def get_datetime(params: GetDatetimeParams) -> str:
    """Întoarce data și ora curentă pentru un fus orar dat (format ISO).

    Folosește-l când utilizatorul întreabă „ce dată/oră e azi" sau are nevoie de
    timpul curent — modelul nu cunoaște momentul prezent.
    """
    try:
        tz = ZoneInfo(params.timezone)
    except Exception:
        return f"Eroare: fus orar necunoscut '{params.timezone}'."
    acum = datetime.now(tz)
    return acum.strftime("%Y-%m-%d %H:%M:%S %Z")


# --- Căutare web (gratuit, fără cheie API) ----------------------------------

@register_tool
def web_search(params: WebSearchParams) -> str:
    """Caută pe web informații recente/actuale și întoarce titluri + rezumate.

    Folosește-l pentru date care se schimbă des sau apar după cutoff-ul modelului
    (știri, prețuri, evenimente). NU îl folosi pentru calcule sau raționament simplu.
    """
    # Import „leneș": dacă pachetul lipsește, tool-ul degradează grațios,
    # fără să pice tot agentul.
    try:
        from ddgs import DDGS
    except ImportError:
        try:
            from duckduckgo_search import DDGS  # nume mai vechi al pachetului
        except ImportError:
            return (
                "web_search indisponibil: instalează pachetul 'ddgs' "
                "(pip install ddgs) pentru căutare reală."
            )

    try:
        with DDGS() as ddgs:
            rezultate = list(ddgs.text(params.query, max_results=params.max_results))
    except Exception as e:
        return f"Eroare la căutare: {e}"

    if not rezultate:
        return f"Niciun rezultat pentru '{params.query}'."

    linii = []
    for i, r in enumerate(rezultate, 1):
        titlu = r.get("title", "(fără titlu)")
        corp = r.get("body", "")
        url = r.get("href", "")
        linii.append(f"{i}. {titlu}\n   {corp}\n   {url}")
    return "\n".join(linii)
