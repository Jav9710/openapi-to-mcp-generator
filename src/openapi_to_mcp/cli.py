"""
CLI para el generador OpenAPI-to-MCP.

Proporciona una interfaz de línea de comandos para generar
servidores MCP desde especificaciones OpenAPI.
"""

import logging
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from .generators.server_generator import MCPServerGenerator
from .models import MCPServerConfig, MCPFramework, EndpointFilter
from .parsers.openapi_parser import OpenAPIParser, OpenAPIParserError
from .transformers.resource_transformer import ResourceTransformer
from .transformers.tool_transformer import ToolTransformer
from .endpoint_selector import EndpointSelector

console = Console()
logger = logging.getLogger(__name__)


@click.group()
@click.version_option(version="1.0.0", prog_name="openapi-to-mcp")
@click.option("--verbose", "-v", is_flag=True, help="Habilitar logging verbose")
def cli(verbose: bool):
    """
    OpenAPI to MCP Generator

    Genera servidores MCP a partir de especificaciones OpenAPI.
    """
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )


@cli.command()
@click.argument("spec_path", type=click.Path(exists=True))
@click.option(
    "--output", "-o",
    type=click.Path(),
    default="./output",
    help="Directorio de salida para el servidor generado"
)
@click.option(
    "--service-name", "-n",
    required=True,
    help="Nombre del microservicio"
)
@click.option(
    "--service-prefix", "-p",
    help="Prefijo para tools y resources (default: nombre del servicio)"
)
@click.option(
    "--base-url", "-u",
    help="URL base de la API (sobrescribe la del spec)"
)
@click.option(
    "--environment", "-e",
    type=click.Choice(["development", "staging", "production"]),
    default="production",
    help="Ambiente de despliegue"
)
@click.option(
    "--include-deprecated",
    is_flag=True,
    help="Incluir operaciones marcadas como deprecated"
)
@click.option(
    "--skip-validation",
    is_flag=True,
    help="Omitir validación estricta de OpenAPI"
)
@click.option(
    "--mcp-framework",
    type=click.Choice(["fastmcp", "mcp"]),
    default="fastmcp",
    help="Framework MCP a usar: 'fastmcp' (recomendado, default) o 'mcp' (estándar)"
)
@click.option(
    "--include-endpoints", "-i",
    multiple=True,
    help="Patrones de endpoints a incluir (ej: /v1/users*, /orders/*). Puede usarse múltiples veces."
)
@click.option(
    "--exclude-endpoints", "-x",
    multiple=True,
    help="Patrones de endpoints a excluir (ej: /internal/*, /admin/*). Puede usarse múltiples veces."
)
@click.option(
    "--interactive",
    is_flag=True,
    help="Modo interactivo para seleccionar endpoints manualmente"
)
def generate(
    spec_path: str,
    output: str,
    service_name: str,
    service_prefix: str | None,
    base_url: str | None,
    environment: str,
    include_deprecated: bool,
    skip_validation: bool,
    mcp_framework: str,
    include_endpoints: tuple[str, ...],
    exclude_endpoints: tuple[str, ...],
    interactive: bool,
):
    """
    Genera un servidor MCP desde una especificación OpenAPI.

    SPEC_PATH: Ruta al archivo YAML o JSON de OpenAPI
    """
    console.print(Panel.fit(
        "[bold blue]OpenAPI to MCP Generator[/bold blue]\n"
        f"Generando servidor MCP desde: {spec_path}",
        border_style="blue"
    ))

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:

            # 1. Parsear especificación OpenAPI
            task = progress.add_task("Parseando especificación OpenAPI...", total=None)
            parser = OpenAPIParser(strict_validation=not skip_validation)
            spec = parser.parse(spec_path)
            progress.update(task, completed=True)

            console.print(f"  [green]✓[/green] API: {spec.title} v{spec.version}")
            console.print(f"  [green]✓[/green] Endpoints: {parser.get_operation_count(spec)}")
            console.print(f"  [green]✓[/green] Schemas: {len(spec.components_schemas)}")

            # 2. Determinar URL base
            if not base_url:
                base_url = spec.get_base_url(environment)

            # 3. Crear configuración
            prefix = service_prefix or service_name
            framework = MCPFramework.FASTMCP if mcp_framework == "fastmcp" else MCPFramework.MCP
            config = MCPServerConfig(
                service_name=service_name,
                service_prefix=prefix,
                base_url=base_url,
                mcp_framework=framework,
                environment=environment,
            )

            console.print(f"  [green]✓[/green] Framework: {framework.value}")

            # 4. Configurar filtro de endpoints
            endpoint_filter = None

            if interactive:
                # Modo interactivo: pausar el progress para mostrar el selector
                progress.stop()
                console.print("\n[bold]Selección de endpoints:[/bold]")

                try:
                    selector = EndpointSelector(spec, include_deprecated=include_deprecated)
                    endpoint_filter = selector.interactive_select()

                    if not endpoint_filter.is_empty():
                        console.print(f"  [green]✓[/green] Filtro: {endpoint_filter.get_summary()}")
                    else:
                        console.print("  [green]✓[/green] Sin filtro (todos los endpoints)")

                except ImportError as e:
                    console.print(f"\n[yellow]Advertencia:[/yellow] {e}")
                    console.print("Continuando sin filtro...")

                progress.start()

            elif include_endpoints or exclude_endpoints:
                # Modo patrones
                endpoint_filter = EndpointFilter(
                    include_patterns=list(include_endpoints),
                    exclude_patterns=list(exclude_endpoints),
                )
                console.print(f"  [green]✓[/green] Filtro: {endpoint_filter.get_summary()}")

            # 5. Transformar operaciones a tools
            task = progress.add_task("Transformando operaciones a tools...", total=None)
            tool_transformer = ToolTransformer(
                service_prefix=prefix,
                include_deprecated=include_deprecated,
            )
            tools = tool_transformer.transform(spec, endpoint_filter=endpoint_filter)
            progress.update(task, completed=True)

            console.print(f"  [green]✓[/green] Tools generadas: {len(tools)}")

            # 6. Transformar schemas a resources
            task = progress.add_task("Transformando schemas a resources...", total=None)
            resource_transformer = ResourceTransformer(service_prefix=prefix)
            resources = resource_transformer.transform(spec, tools)
            progress.update(task, completed=True)

            console.print(f"  [green]✓[/green] Resources generados: {len(resources)}")

            # 7. Generar código del servidor
            task = progress.add_task("Generando código del servidor MCP...", total=None)
            generator = MCPServerGenerator(output_dir=output)
            result = generator.generate(
                spec=spec,
                tools=tools,
                resources=resources,
                config=config,
            )
            progress.update(task, completed=True)

        # Mostrar resultado
        if result.success:
            console.print()
            console.print(Panel.fit(
                f"[bold green]Servidor MCP generado exitosamente[/bold green]\n\n"
                f"Ubicación: {result.output_path}\n"
                f"Tools: {len(result.tools_generated)}\n"
                f"Resources: {len(result.resources_generated)}",
                border_style="green"
            ))

            console.print("\n[bold]Próximos pasos:[/bold]")
            console.print(f"  1. cd {result.output_path}")
            console.print("  2. cp .env.example .env")
            console.print("  3. Edita .env con tus credenciales")
            console.print("  4. pip install -r requirements.txt")
            console.print("  5. python -m src.server")

            # Mostrar advertencias si las hay
            if result.warnings:
                console.print("\n[yellow]Advertencias:[/yellow]")
                for warning in result.warnings:
                    console.print(f"  [yellow]![/yellow] {warning}")

        else:
            console.print()
            console.print(Panel.fit(
                "[bold red]Error generando servidor[/bold red]\n\n" +
                "\n".join(result.errors),
                border_style="red"
            ))
            sys.exit(1)

    except OpenAPIParserError as e:
        console.print(f"\n[red]Error parseando OpenAPI:[/red] {e}")
        sys.exit(1)

    except Exception as e:
        console.print(f"\n[red]Error inesperado:[/red] {e}")
        logger.exception("Error durante la generación")
        sys.exit(1)


@cli.command()
@click.argument("spec_path", type=click.Path(exists=True))
@click.option("--skip-validation", is_flag=True, help="Omitir validación estricta")
def validate(spec_path: str, skip_validation: bool):
    """
    Valida una especificación OpenAPI.

    SPEC_PATH: Ruta al archivo YAML o JSON de OpenAPI
    """
    console.print(f"Validando: {spec_path}")

    try:
        parser = OpenAPIParser(strict_validation=not skip_validation)
        spec = parser.parse(spec_path)

        console.print(Panel.fit(
            f"[bold green]Especificación válida[/bold green]\n\n"
            f"Título: {spec.title}\n"
            f"Versión: {spec.version}\n"
            f"OpenAPI: {spec.openapi_version}\n"
            f"Endpoints: {parser.get_operation_count(spec)}\n"
            f"Schemas: {len(spec.components_schemas)}\n"
            f"Security Schemes: {len(spec.security_schemes)}",
            border_style="green"
        ))

    except OpenAPIParserError as e:
        console.print(Panel.fit(
            f"[bold red]Especificación inválida[/bold red]\n\n{e}",
            border_style="red"
        ))
        sys.exit(1)


@cli.command()
@click.argument("spec_path", type=click.Path(exists=True))
@click.option("--service-prefix", "-p", default="api", help="Prefijo para el servicio")
def preview(spec_path: str, service_prefix: str):
    """
    Vista previa de tools y resources que se generarían.

    SPEC_PATH: Ruta al archivo YAML o JSON de OpenAPI
    """
    console.print(f"Analizando: {spec_path}\n")

    try:
        # Parsear
        parser = OpenAPIParser(strict_validation=False)
        spec = parser.parse(spec_path)

        # Transformar
        tool_transformer = ToolTransformer(service_prefix=service_prefix)
        tools = tool_transformer.transform(spec)

        resource_transformer = ResourceTransformer(service_prefix=service_prefix)
        resources = resource_transformer.transform(spec, tools)

        # Mostrar tabla de tools
        console.print("[bold]Tools que se generarían:[/bold]\n")

        tools_table = Table(show_header=True, header_style="bold blue")
        tools_table.add_column("Nombre", style="cyan")
        tools_table.add_column("Método", width=8)
        tools_table.add_column("Endpoint")
        tools_table.add_column("Params", justify="right")

        for tool in tools[:30]:
            tools_table.add_row(
                tool.name,
                tool.http_method.value.upper(),
                tool.endpoint_path,
                str(len(tool.parameters))
            )

        console.print(tools_table)

        if len(tools) > 30:
            console.print(f"  ... y {len(tools) - 30} tools más\n")

        # Mostrar tabla de resources
        console.print("\n[bold]Resources que se generarían:[/bold]\n")

        resources_table = Table(show_header=True, header_style="bold green")
        resources_table.add_column("URI", style="cyan")
        resources_table.add_column("Nombre")
        resources_table.add_column("Tipo")

        for resource in resources[:20]:
            res_type = "Colección" if resource.is_collection else "Entidad"
            if "schemas" in resource.uri:
                res_type = "Schema"
            elif "documentation" in resource.uri:
                res_type = "Doc"

            resources_table.add_row(
                resource.uri,
                resource.name,
                res_type
            )

        console.print(resources_table)

        if len(resources) > 20:
            console.print(f"  ... y {len(resources) - 20} resources más\n")

        # Resumen
        console.print(Panel.fit(
            f"[bold]Resumen[/bold]\n\n"
            f"Total Tools: {len(tools)}\n"
            f"Total Resources: {len(resources)}\n"
            f"Schemas: {len(spec.components_schemas)}\n"
            f"Security Schemes: {', '.join(spec.security_schemes.keys()) or 'Ninguno'}",
            border_style="blue"
        ))

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)


@cli.command()
@click.argument("config_file", type=click.Path(exists=True))
def batch(config_file: str):
    """
    Genera servidores MCP para múltiples microservicios.

    CONFIG_FILE: Archivo YAML con configuración de microservicios
    """
    import yaml

    console.print(f"Procesando configuración batch: {config_file}\n")

    try:
        with open(config_file, "r") as f:
            batch_config = yaml.safe_load(f)

        services = batch_config.get("services", [])
        output_dir = batch_config.get("output_dir", "./output")
        global_settings = batch_config.get("global", {})

        console.print(f"Servicios a procesar: {len(services)}\n")

        results = []

        for service in services:
            service_name = service.get("name")
            spec_path = service.get("spec")

            console.print(f"[bold]Procesando: {service_name}[/bold]")

            try:
                # Parsear
                parser = OpenAPIParser(strict_validation=False)
                spec = parser.parse(spec_path)

                # Configuración
                config = MCPServerConfig(
                    service_name=service_name,
                    service_prefix=service.get("prefix", service_name),
                    base_url=service.get("base_url") or spec.get_base_url(),
                    environment=service.get("environment", global_settings.get("environment", "production")),
                )

                # Transformar
                tool_transformer = ToolTransformer(service_prefix=config.service_prefix)
                tools = tool_transformer.transform(spec)

                resource_transformer = ResourceTransformer(service_prefix=config.service_prefix)
                resources = resource_transformer.transform(spec, tools)

                # Generar
                generator = MCPServerGenerator(output_dir=output_dir)
                result = generator.generate(spec, tools, resources, config)

                status = "[green]✓[/green]" if result.success else "[red]✗[/red]"
                console.print(f"  {status} {service_name}: {len(tools)} tools, {len(resources)} resources")

                results.append({
                    "service": service_name,
                    "success": result.success,
                    "tools": len(tools),
                    "resources": len(resources),
                })

            except Exception as e:
                console.print(f"  [red]✗[/red] {service_name}: {e}")
                results.append({
                    "service": service_name,
                    "success": False,
                    "error": str(e),
                })

        # Resumen final
        successful = sum(1 for r in results if r.get("success"))
        console.print(Panel.fit(
            f"[bold]Proceso batch completado[/bold]\n\n"
            f"Exitosos: {successful}/{len(services)}\n"
            f"Output: {output_dir}",
            border_style="green" if successful == len(services) else "yellow"
        ))

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)


@cli.command()
@click.argument("spec_path", type=click.Path(exists=True))
@click.option(
    "--port", "-p",
    type=int,
    default=5000,
    help="Puerto para el servidor web (default: 5000)"
)
@click.option(
    "--no-browser",
    is_flag=True,
    help="No abrir el navegador automáticamente"
)
@click.option(
    "--output", "-o",
    type=click.Path(),
    default="./output",
    help="Directorio de salida para el servidor generado"
)
def gui(spec_path: str, port: int, no_browser: bool, output: str):
    """
    Abre interfaz gráfica web para seleccionar endpoints.

    SPEC_PATH: Ruta al archivo YAML o JSON de OpenAPI

    La interfaz permite:
    - Ver todos los endpoints de forma visual
    - Filtrar por tags o búsqueda
    - Seleccionar endpoints arrastrando entre listas
    - Generar el servidor MCP con la selección
    """
    console.print(Panel.fit(
        "[bold blue]OpenAPI to MCP Generator - GUI Mode[/bold blue]\n"
        f"Cargando: {spec_path}",
        border_style="blue"
    ))

    try:
        # Parsear especificación
        parser = OpenAPIParser(strict_validation=False)
        spec = parser.parse(spec_path)

        console.print(f"  [green]✓[/green] API: {spec.title} v{spec.version}")
        console.print(f"  [green]✓[/green] Endpoints: {parser.get_operation_count(spec)}")

        # Importar y lanzar GUI
        try:
            from .gui.web_app import create_app, run_gui
        except ImportError as e:
            console.print(f"\n[red]Error:[/red] Flask no está instalado.")
            console.print("Instálalo con: pip install flask")
            sys.exit(1)

        console.print(f"\n[bold]Iniciando servidor web en http://localhost:{port}[/bold]")

        if not no_browser:
            console.print("Abriendo navegador...")

        run_gui(
            spec=spec,
            spec_path=spec_path,
            output_dir=output,
            port=port,
            open_browser=not no_browser,
        )

    except OpenAPIParserError as e:
        console.print(f"\n[red]Error parseando OpenAPI:[/red] {e}")
        sys.exit(1)

    except Exception as e:
        console.print(f"\n[red]Error:[/red] {e}")
        logger.exception("Error en GUI")
        sys.exit(1)


def main():
    """Punto de entrada principal."""
    cli()


if __name__ == "__main__":
    main()
