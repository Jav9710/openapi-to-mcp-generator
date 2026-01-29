#!/usr/bin/env python3
"""
Demostración de uso del generador OpenAPI-to-MCP.

Este script muestra cómo usar el generador programáticamente
para convertir una especificación OpenAPI en un servidor MCP.
"""

import sys
from pathlib import Path

# Agregar el directorio src al path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from openapi_to_mcp import (
    OpenAPIParser,
    ToolTransformer,
    ResourceTransformer,
    MCPServerGenerator,
    MCPServerConfig,
)


def main():
    """Ejecuta la demostración completa."""
    print("=" * 60)
    print("OpenAPI to MCP Generator - Demostración")
    print("=" * 60)

    # Ruta al archivo de ejemplo
    spec_path = Path(__file__).parent / "user-management-api.yaml"

    if not spec_path.exists():
        print(f"Error: No se encontró el archivo {spec_path}")
        return

    # 1. PARSING
    print("\n[1] Parseando especificación OpenAPI...")
    print("-" * 40)

    parser = OpenAPIParser(strict_validation=False)
    spec = parser.parse(spec_path)

    print(f"  Título: {spec.title}")
    print(f"  Versión: {spec.version}")
    print(f"  OpenAPI: {spec.openapi_version}")
    print(f"  Servidores: {len(spec.servers)}")
    for server in spec.servers:
        print(f"    - {server.url} ({server.description})")
    print(f"  Endpoints: {parser.get_operation_count(spec)}")
    print(f"  Schemas: {len(spec.components_schemas)}")
    print(f"  Security Schemes: {list(spec.security_schemes.keys())}")

    # 2. TRANSFORMACIÓN A TOOLS
    print("\n[2] Transformando operaciones a Tools MCP...")
    print("-" * 40)

    tool_transformer = ToolTransformer(
        service_prefix="users",
        include_deprecated=False,
    )
    tools = tool_transformer.transform(spec)

    print(f"  Tools generadas: {len(tools)}")
    print("\n  Primeras 10 tools:")
    for tool in tools[:10]:
        params_count = len(tool.parameters)
        has_body = "+" if tool.request_body_schema else ""
        print(f"    - {tool.name}")
        print(f"      {tool.http_method.value.upper()} {tool.endpoint_path}")
        print(f"      Params: {params_count}{has_body}")

    # Mostrar resumen por método HTTP
    summary = tool_transformer.get_tools_summary(tools)
    print(f"\n  Resumen por método HTTP:")
    for method, count in summary["by_method"].items():
        print(f"    {method.upper()}: {count}")

    # 3. TRANSFORMACIÓN A RESOURCES
    print("\n[3] Transformando schemas a Resources MCP...")
    print("-" * 40)

    resource_transformer = ResourceTransformer(
        service_prefix="users",
        generate_entity_resources=True,
    )
    resources = resource_transformer.transform(spec, tools)

    print(f"  Resources generados: {len(resources)}")
    print("\n  Primeros 10 resources:")
    for resource in resources[:10]:
        res_type = "collection" if resource.is_collection else "entity"
        if "schemas" in resource.uri:
            res_type = "schema"
        elif "documentation" in resource.uri:
            res_type = "docs"
        print(f"    - {resource.uri}")
        print(f"      Nombre: {resource.name} ({res_type})")

    # Mostrar resumen
    res_summary = resource_transformer.get_resources_summary(resources)
    print(f"\n  Resumen por tipo:")
    print(f"    Schemas: {res_summary['schemas']}")
    print(f"    Entidades: {res_summary['entities']}")
    print(f"    Colecciones: {res_summary['collections']}")
    print(f"    Documentación: {res_summary['documentation']}")

    # 4. GENERACIÓN DEL SERVIDOR MCP
    print("\n[4] Generando servidor MCP...")
    print("-" * 40)

    config = MCPServerConfig(
        service_name="user_management",
        service_prefix="users",
        base_url=spec.get_base_url("production"),
        environment="production",
        timeout=30,
        auth_config={
            "type": "bearer",
        },
        headers={
            "User-Agent": "MCP-Server-UserManagement/1.0",
        },
    )

    output_dir = Path(__file__).parent.parent / "output"
    generator = MCPServerGenerator(output_dir=output_dir)

    result = generator.generate(
        spec=spec,
        tools=tools,
        resources=resources,
        config=config,
    )

    if result.success:
        print(f"  ✓ Servidor generado exitosamente")
        print(f"  Output: {result.output_path}")
        print(f"  Tools: {len(result.tools_generated)}")
        print(f"  Resources: {len(result.resources_generated)}")

        print("\n  Archivos generados:")
        output_path = Path(result.output_path)
        for file in sorted(output_path.rglob("*")):
            if file.is_file():
                rel_path = file.relative_to(output_path)
                print(f"    - {rel_path}")
    else:
        print(f"  ✗ Error en la generación:")
        for error in result.errors:
            print(f"    - {error}")

    # 5. EJEMPLO DE TOOL GENERADA
    print("\n[5] Ejemplo de Tool generada (listUsers)...")
    print("-" * 40)

    list_users_tool = next(
        (t for t in tools if "list_users" in t.name.lower()),
        tools[0]
    )

    print(f"  Nombre: {list_users_tool.name}")
    print(f"  Operación: {list_users_tool.operation_id}")
    print(f"  Método: {list_users_tool.http_method.value.upper()}")
    print(f"  Endpoint: {list_users_tool.endpoint_path}")
    print(f"  Tags: {list_users_tool.tags}")
    print(f"\n  Descripción:")
    print(f"    {list_users_tool.description[:200]}...")

    print(f"\n  Parámetros:")
    for param in list_users_tool.parameters:
        req = "(requerido)" if param.required else "(opcional)"
        print(f"    - {param.name}: {param.param_type} {req}")
        print(f"      {param.description[:60]}...")

    print(f"\n  Input Schema (JSON Schema):")
    import json
    schema = list_users_tool.get_input_schema()
    print(json.dumps(schema, indent=4, ensure_ascii=False)[:500] + "...")

    # 6. PRÓXIMOS PASOS
    print("\n" + "=" * 60)
    print("Próximos pasos:")
    print("=" * 60)
    print(f"""
1. Navegar al servidor generado:
   cd {result.output_path}

2. Configurar credenciales:
   cp .env.example .env
   # Editar .env con tus credenciales

3. Instalar dependencias:
   pip install -r requirements.txt

4. Ejecutar el servidor:
   python -m src.server

5. Integrar con Claude Desktop:
   Agregar configuración en claude_desktop_config.json
""")


def show_tool_invocation_example():
    """Muestra ejemplo de cómo un LLM invocaría una tool."""
    print("\n" + "=" * 60)
    print("Ejemplo de invocación de Tool por un LLM")
    print("=" * 60)

    example = """
Usuario: "Muéstrame los usuarios administradores de la página 2"

LLM analiza la solicitud y decide usar la tool users_list_users:

<tool_call>
  name: users_list_users
  arguments:
    page: 2
    role: "admin"
    size: 20
</tool_call>

El servidor MCP ejecuta:
  1. Construye la URL: GET /users?page=2&role=admin&size=20
  2. Agrega headers de autenticación (Bearer token)
  3. Agrega Correlation-ID para tracing
  4. Ejecuta la petición HTTP
  5. Retorna el resultado al LLM

Respuesta:
{
  "content": [
    {"id": "uuid-1", "username": "admin1", "email": "admin1@example.com"},
    {"id": "uuid-2", "username": "admin2", "email": "admin2@example.com"}
  ],
  "page": 2,
  "size": 20,
  "totalElements": 45,
  "totalPages": 3
}

LLM: "Encontré 2 usuarios administradores en la página 2.
      Hay un total de 45 administradores distribuidos en 3 páginas."
"""
    print(example)


if __name__ == "__main__":
    main()
    show_tool_invocation_example()
