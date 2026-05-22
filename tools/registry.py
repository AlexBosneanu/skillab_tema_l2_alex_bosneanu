"""Registry central de tool-uri + decoratorul @register_tool (slide 57).

Convenție din curs: tool-urile NU primesc un obiect registry prin parametri — ele
doar se decorează cu @register_tool, iar decoratorul le înscrie automat în dict-ul
global TOOL_REGISTRY. Astfel "registry-ul nu știe de tools, dar tools știu de registry".
"""

import inspect

from pydantic import BaseModel

# Dict global: numele tool-ului -> metadate despre el.
# Cheie = func.__name__ (ex. "calculator"); valoare = {"func", "params_model", "description"}.
TOOL_REGISTRY: dict[str, dict] = {}


def register_tool(func):
    """Înregistrează o funcție-tool în TOOL_REGISTRY.

    Validează la momentul IMPORTULUI (fail-fast), nu la runtime:
      1. funcția are EXACT un parametru, de tip Pydantic BaseModel;
      2. funcția are docstring (devine `description` vizibil pentru LLM), min 15 caractere.
    Un tool prost definit oprește programul la pornire, nu mai târziu, în producție.
    """
    sig = inspect.signature(func)
    params = list(sig.parameters.values())

    # Validare 1: un singur param de tip BaseModel
    if len(params) != 1 or not (
        isinstance(params[0].annotation, type)
        and issubclass(params[0].annotation, BaseModel)
    ):
        raise TypeError(
            f"{func.__name__}: param unic de tip BaseModel obligatoriu"
        )

    # Validare 2: docstring obligatoriu (devine description pentru LLM)
    docstring = (func.__doc__ or "").strip()
    if not docstring:
        raise ValueError(
            f"{func.__name__}: docstring obligatoriu — devine "
            f"description vizibil pentru LLM."
        )
    if len(docstring) < 15:
        raise ValueError(
            f"{func.__name__}: docstring prea scurt ({len(docstring)} "
            f"caractere). LLM-ul are nevoie de min 15 ca să decidă."
        )

    TOOL_REGISTRY[func.__name__] = {
        "func": func,
        "params_model": params[0].annotation,
        "description": docstring,  # <- exact asta primește LLM-ul
    }
    return func
