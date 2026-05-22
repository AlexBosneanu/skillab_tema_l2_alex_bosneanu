"""Pachetul `tools` — exportă ToolWrapper.

IMPORTANT: importăm `basic_tools` AICI ca să se execute decoratorii @register_tool
și să se umple TOOL_REGISTRY chiar la importul pachetului. Fără acest import,
catalogul ar fi gol (tool-urile nu s-ar fi înregistrat încă).
"""

from . import basic_tools  # noqa: F401  (efect secundar: înregistrează tool-urile)
from .registry import TOOL_REGISTRY, register_tool
from .tool_wrapper import ToolWrapper

__all__ = ["ToolWrapper", "TOOL_REGISTRY", "register_tool"]
