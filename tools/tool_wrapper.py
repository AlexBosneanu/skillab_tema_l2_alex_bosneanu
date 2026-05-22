"""ToolWrapper: punct unic de execuție (call) și de expunere (catalog) a tool-urilor.

- call(name, args): Lookup -> Validare Pydantic -> Execuție -> Return (string).
  Identic cu slide 59. Erorile devin string-uri (nu excepții), ca să nu pice bucla
  ReAct și ca LLM-ul să poată CITI eroarea și să se autocorecteze.
- catalog(): expune tool-urile către LLM ca JSON Schema. Aici e SINGURA adaptare la
  furnizor: pentru Gemini/LangChain (`bind_tools`) folosim formatul "function-calling".
"""

from .registry import TOOL_REGISTRY


class ToolWrapper:
    @staticmethod
    def call(name: str, args: dict) -> str:
        # 1. Lookup în registry
        if name not in TOOL_REGISTRY:
            return f"Eroare: tool '{name}' nu există."

        tool = TOOL_REGISTRY[name]

        # 2. Validate — Pydantic verifică tipuri și constrângeri
        try:
            params = tool["params_model"](**args)
        except Exception as e:
            return f"Eroare validare pentru '{name}': {e}"

        # 3. Execute + 4. Return (ca string, ca să-l putem trimite înapoi modelului)
        try:
            return str(tool["func"](params))
        except Exception as e:
            return f"Eroare execuție '{name}': {e}"

    @staticmethod
    def catalog() -> list[dict]:
        """Catalog în format function-calling pentru Gemini prin `llm.bind_tools(...)`.

        Pydantic generează automat JSON Schema-ul (`model_json_schema()`); îl
        împachetăm în formatul pe care LangChain îl convertește către Gemini.
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": tool["description"],
                    "parameters": tool["params_model"].model_json_schema(),
                },
            }
            for name, tool in TOOL_REGISTRY.items()
        ]

    @staticmethod
    def catalog_anthropic() -> list[dict]:
        """Varianta din curs (slide 59) — formatul nativ Anthropic.

        Aceleași date, alt „ambalaj": Anthropic pune `input_schema` la rădăcină.
        O păstrăm ca referință didactică; agentul nostru (Gemini) folosește catalog().
        """
        return [
            {
                "name": name,
                "description": tool["description"],
                "input_schema": tool["params_model"].model_json_schema(),
            }
            for name, tool in TOOL_REGISTRY.items()
        ]
