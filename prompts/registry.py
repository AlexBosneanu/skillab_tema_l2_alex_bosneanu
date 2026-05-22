"""PromptRegistry: prompturile sunt CONFIGURAȚIE (fișiere YAML), nu cod (slide 24-28).

Idee centrală din curs: "Configurația trăiește în fișiere, nu în cod". Modifici un
prompt fără redeploy, îl versionezi în Git, poți testa variații.

Flux: fișiere .yaml -> PromptTemplate -> render cu Jinja2 (variabile dinamice).
"""

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml
from jinja2 import Template


@dataclass(frozen=True)
class PromptTemplate:
    # Reprezentarea internă a unui fișier YAML de prompt (slide 26).
    # `frozen=True` => imutabil: odată încărcat, nu-l modifici accidental.
    name: str
    version: str
    prompt: str
    description: str = ""


class PromptRegistry:
    def __init__(self, folder: str | Path):
        self._folder = Path(folder)
        self._templates = self._load(self._folder)

    def _load(self, folder: Path) -> dict[str, PromptTemplate]:
        # Citește toate .yaml din folder -> dict {name: PromptTemplate}
        templates: dict[str, PromptTemplate] = {}
        for path in folder.rglob("*.yaml"):
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
            tpl = PromptTemplate(**data)
            templates[tpl.name] = tpl
        return templates

    def get(self, name: str) -> PromptTemplate:
        # Recuperează un template după nume (fără render).
        return self._templates[name]

    def list_templates(self) -> list[str]:
        # Vede tot ce există în catalog.
        return sorted(self._templates)

    def render(self, name: str, **variabile) -> str:
        # Validează existența + aplică Jinja2 cu variabilele primite.
        template = self._templates[name]
        return Template(template.prompt).render(**variabile)

    def reload(self) -> None:
        # Reîncarcă YAML-urile de pe disk (util în dev: editezi -> reload -> testezi).
        self._templates = self._load(self._folder)


# Folderul cu YAML-uri, rezolvat relativ la ACEST fișier => merge din orice director.
# (Mică îmbunătățire față de slide 28, care hardcoda "prompts/".)
_PROMPTS_DIR = Path(__file__).parent


@lru_cache(maxsize=1)
def get_prompt_registry() -> PromptRegistry:
    # Singleton via lru_cache: o singură încărcare YAML, reutilizată în tot codul.
    return PromptRegistry(folder=_PROMPTS_DIR)
