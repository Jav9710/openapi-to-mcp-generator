"""
Módulo GUI para el generador OpenAPI-to-MCP.

Proporciona una interfaz web para seleccionar endpoints de forma visual.
"""

from .web_app import create_app, run_gui

__all__ = ["create_app", "run_gui"]
