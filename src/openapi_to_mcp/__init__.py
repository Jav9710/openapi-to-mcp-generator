"""
OpenAPI to MCP Generator

Generador automático de servidores MCP (Model Context Protocol)
a partir de especificaciones OpenAPI 3.0/3.1.

Permite que los LLMs interactúen con microservicios empresariales
de forma estandarizada.
"""

__version__ = "1.0.0"
__author__ = "Enterprise Team"

from .models import (
    MCPTool,
    MCPResource,
    MCPServerConfig,
    OpenAPISpec,
    SecurityScheme,
    ToolParameter,
)
from .parsers.openapi_parser import OpenAPIParser
from .transformers.tool_transformer import ToolTransformer
from .transformers.resource_transformer import ResourceTransformer
from .generators.server_generator import MCPServerGenerator

__all__ = [
    "MCPTool",
    "MCPResource",
    "MCPServerConfig",
    "OpenAPISpec",
    "SecurityScheme",
    "ToolParameter",
    "OpenAPIParser",
    "ToolTransformer",
    "ResourceTransformer",
    "MCPServerGenerator",
]
