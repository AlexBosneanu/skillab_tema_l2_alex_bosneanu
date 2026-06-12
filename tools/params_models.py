"""Modele Pydantic pentru parametrii fiecărui tool (slide 56).

De ce Pydantic: un singur loc definește tipurile, validările, default-urile și
descrierile. Din el:
  - generăm automat JSON Schema-ul pe care îl vede LLM-ul (`.model_json_schema()`);
  - validăm input-ul ÎNAINTE de execuția tool-ului (erori clare, nu crash-uri).
`Field(description=...)` ajunge în schema trimisă modelului, deci scrie descrieri utile.
"""

from pydantic import BaseModel, Field


class CalculatorParams(BaseModel):
    expression: str = Field(
        description="Expresia matematică de evaluat (ex: '2 + 3 * 4')",
        min_length=1,
    )


class GetDatetimeParams(BaseModel):
    timezone: str = Field(
        default="Europe/Bucharest",
        description=(
            "Fusul orar IANA pentru care vrei data/ora curentă "
            "(ex: 'Europe/Bucharest', 'UTC', 'America/New_York')."
        ),
    )


class WebSearchParams(BaseModel):
    query: str = Field(
        description="Termenii de căutat pe web",
        min_length=2,
    )
    max_results: int = Field(
        default=5,
        description="Numărul maxim de rezultate returnate",
        ge=1,
        le=20,
    )


class SearchDocumentsParams(BaseModel):
    query: str = Field(
        description="Întrebarea sau subiectul de căutat în documentele stocate (facturi, contracte, rapoarte)",
        min_length=2,
    )
    top_k: int = Field(
        default=3,
        description="Numărul de fragmente relevante de returnat",
        ge=1,
        le=10,
    )
