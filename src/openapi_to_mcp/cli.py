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
            task = progress.add_task("Generando código del servidor MCP...", total=100)

            def progress_callback(description: str, current: int, total: int):
                """Callback para actualizar la progress bar."""
                percentage = int((current / total) * 100)
                progress.update(task, completed=percentage, description=f"[cyan]{description}[/cyan]")

            generator = MCPServerGenerator(output_dir=output)
            result = generator.generate(
                spec=spec,
                tools=tools,
                resources=resources,
                config=config,
                progress_callback=progress_callback,
            )
            progress.update(task, completed=100, description="[green]Código generado exitosamente[/green]")

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
@click.argument("spec_path", type=click.Path(exists=True), required=False)
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
def gui(spec_path: str | None, port: int, no_browser: bool, output: str):
    """
    Abre interfaz gráfica web para seleccionar endpoints.

    SPEC_PATH: Ruta al archivo YAML o JSON de OpenAPI (opcional)

    Si no se proporciona SPEC_PATH, se abre en modo standalone
    donde puedes subir archivos o cargar desde URL.

    La interfaz permite:
    - Subir archivos OpenAPI o cargar desde URL
    - Ver todos los endpoints de forma visual
    - Filtrar por tags o búsqueda
    - Seleccionar endpoints arrastrando entre listas
    - Generar y descargar el servidor MCP como ZIP
    """
    # Importar y verificar Flask
    try:
        from .gui.web_app import run_gui, run_standalone
    except ImportError:
        console.print(f"\n[red]Error:[/red] Flask no está instalado.")
        console.print("Instálalo con: pip install 'openapi-to-mcp[gui]'")
        sys.exit(1)

    if spec_path:
        # Modo con spec pre-cargado
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

    else:
        # Modo standalone (sin spec)
        console.print(Panel.fit(
            "[bold blue]OpenAPI to MCP Generator - Web Mode[/bold blue]\n"
            "Modo standalone: sube archivos o carga desde URL",
            border_style="blue"
        ))

        console.print(f"\n[bold]Iniciando servidor web en http://localhost:{port}[/bold]")

        if not no_browser:
            console.print("Abriendo navegador...")

        run_gui(
            spec=None,
            spec_path=None,
            output_dir=output,
            port=port,
            open_browser=not no_browser,
            standalone=True,
        )


@cli.command()
@click.option(
    "--port", "-p",
    type=int,
    default=5000,
    help="Puerto para el servidor web (default: 5000)"
)
@click.option(
    "--output", "-o",
    type=click.Path(),
    default="./output",
    help="Directorio de salida para servidores generados"
)
@click.option(
    "--no-browser",
    is_flag=True,
    help="No abrir el navegador automáticamente"
)
def serve(port: int, output: str, no_browser: bool):
    """
    Inicia el servidor web en modo standalone.

    En este modo puedes:
    - Subir archivos OpenAPI desde tu computadora
    - Cargar especificaciones desde URLs remotas
    - Seleccionar endpoints visualmente
    - Generar y descargar servidores MCP como ZIP

    Ideal para desplegar como servicio Docker.
    """
    try:
        from .gui.web_app import run_gui
    except ImportError:
        console.print(f"\n[red]Error:[/red] Flask no está instalado.")
        console.print("Instálalo con: pip install 'openapi-to-mcp[gui]'")
        sys.exit(1)

    console.print(Panel.fit(
        "[bold blue]OpenAPI to MCP Generator - Web Service[/bold blue]\n"
        "Servidor standalone para generación de MCP",
        border_style="blue"
    ))

    console.print(f"\n[bold]Servidor corriendo en http://localhost:{port}[/bold]")
    console.print("Presiona Ctrl+C para detener\n")

    run_gui(
        spec=None,
        spec_path=None,
        output_dir=output,
        port=port,
        open_browser=not no_browser,
        standalone=True,
    )


@cli.command()
@click.argument("spec_path", type=click.Path(exists=True))
@click.option("--detailed", "-d", is_flag=True, help="Mostrar análisis detallado por endpoint")
@click.option("--json", "output_json", is_flag=True, help="Salida en formato JSON")
def score(spec_path: str, detailed: bool, output_json: bool):
    """
    Calcula el MCP Utility Score de una especificación OpenAPI.

    SPEC_PATH: Ruta al archivo YAML o JSON de OpenAPI

    El score indica qué tan útil será el MCP generado para los LLMs.
    Un score alto significa mejor documentación y descripciones.
    """
    import json
    import yaml

    try:
        from .validators import MCPUtilityScorer

        # Cargar spec como dict
        with open(spec_path, "r", encoding="utf-8") as f:
            content = f.read()
            if spec_path.endswith(".json"):
                raw_spec = json.loads(content)
            else:
                raw_spec = yaml.safe_load(content)

        # Calcular score
        scorer = MCPUtilityScorer()
        result = scorer.calculate_score(raw_spec)

        if output_json:
            import json as json_module
            console.print(json_module.dumps(result.to_dict(), indent=2))
            return

        # Mostrar resultados con Rich
        grade_colors = {"A": "green", "B": "blue", "C": "yellow", "D": "orange1", "F": "red"}
        grade_color = grade_colors.get(result.grade, "white")

        console.print(Panel.fit(
            f"[bold]MCP Utility Score[/bold]\n\n"
            f"[bold {grade_color}]{result.overall_score}/100[/bold {grade_color}] "
            f"(Grade: [{grade_color}]{result.grade}[/{grade_color}])\n\n"
            f"Endpoints analizados: {result.total_endpoints}\n"
            f"Necesitan atención: {result.endpoints_needing_attention}",
            border_style=grade_color
        ))

        # Mostrar categorías
        console.print("\n[bold]Desglose por categoría:[/bold]\n")

        score_table = Table(show_header=True, header_style="bold")
        score_table.add_column("Categoría", width=20)
        score_table.add_column("Score", justify="right", width=10)
        score_table.add_column("Completos", justify="right", width=12)
        score_table.add_column("Barra", width=30)

        for name, cat in result.categories.items():
            bar = "█" * (cat.score // 5) + "░" * (20 - cat.score // 5)
            color = "green" if cat.score >= 75 else "yellow" if cat.score >= 50 else "red"
            score_table.add_row(
                cat.name,
                f"[{color}]{cat.score}%[/{color}]",
                f"{cat.complete_items}/{cat.total_items}",
                f"[{color}]{bar}[/{color}]"
            )

        console.print(score_table)

        # Mostrar recomendaciones
        if result.recommendations:
            console.print("\n[bold]Recomendaciones:[/bold]\n")
            for rec in result.recommendations:
                console.print(f"  {rec}")

        # Mostrar endpoints con problemas si se pide detalle
        if detailed and result.incomplete_endpoints:
            console.print(f"\n[bold]Endpoints que necesitan atención ({len(result.incomplete_endpoints)}):[/bold]\n")

            for i, ep in enumerate(result.incomplete_endpoints[:20], 1):
                priority_color = {"high": "red", "medium": "yellow", "low": "blue"}[ep.priority.value]
                console.print(
                    f"  {i}. [{priority_color}][{ep.priority.value.upper()}][/{priority_color}] "
                    f"[cyan]{ep.method.upper()}[/cyan] {ep.path}"
                )
                console.print(f"     Falta: {', '.join(ep.missing_fields)}")

            if len(result.incomplete_endpoints) > 20:
                console.print(f"\n  ... y {len(result.incomplete_endpoints) - 20} más")

        # Sugerencia de enriquecimiento
        if result.overall_score < 80:
            console.print(f"\n[yellow]Tip:[/yellow] Usa 'openapi-to-mcp enrich {spec_path}' para mejorar la especificación.")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)


@cli.command()
@click.argument("spec_path", type=click.Path(exists=True))
@click.option("--output", "-o", type=click.Path(), help="Ruta para guardar el spec enriquecido")
@click.option("--auto", is_flag=True, help="Usar sugerencias automáticas sin preguntar")
def enrich(spec_path: str, output: str | None, auto: bool):
    """
    Enriquece una especificación OpenAPI con información faltante.

    SPEC_PATH: Ruta al archivo YAML o JSON de OpenAPI

    Modo interactivo: te guía para completar descripciones, tags
    y operationIds faltantes endpoint por endpoint.

    Modo auto (--auto): aplica todas las sugerencias automáticamente.
    """
    import json
    import yaml

    try:
        from .validators import MCPUtilityScorer, EnrichmentData

        # Cargar spec
        with open(spec_path, "r", encoding="utf-8") as f:
            content = f.read()
            is_json = spec_path.endswith(".json")
            if is_json:
                raw_spec = json.loads(content)
            else:
                raw_spec = yaml.safe_load(content)

        # Calcular score inicial
        scorer = MCPUtilityScorer()
        initial_score = scorer.calculate_score(raw_spec)

        console.print(Panel.fit(
            f"[bold]MCP Enrichment Tool[/bold]\n\n"
            f"Score actual: [{'green' if initial_score.overall_score >= 80 else 'yellow'}]"
            f"{initial_score.overall_score}/100[/]\n"
            f"Endpoints a enriquecer: {initial_score.endpoints_needing_attention}",
            border_style="blue"
        ))

        if initial_score.endpoints_needing_attention == 0:
            console.print("\n[green]¡La especificación ya está bien documentada![/green]")
            return

        # Recopilar enrichments
        enrichments = []

        if auto:
            # Modo automático: usar todas las sugerencias
            console.print("\n[bold]Aplicando sugerencias automáticas...[/bold]\n")

            for ep in initial_score.incomplete_endpoints:
                enrichment = EnrichmentData(
                    method=ep.method,
                    path=ep.path,
                    description=ep.suggested_values.get("description"),
                    operation_id=ep.suggested_values.get("operationId"),
                    tags=ep.suggested_values.get("tags", []),
                )
                enrichments.append(enrichment)
                console.print(f"  [green]✓[/green] {ep.method.upper()} {ep.path}")

        else:
            # Modo interactivo
            try:
                import questionary
            except ImportError:
                console.print(f"\n[red]Error:[/red] questionary no está instalado.")
                console.print("Instálalo con: pip install 'openapi-to-mcp[interactive]'")
                console.print("\nAlternativamente, usa --auto para aplicar sugerencias automáticamente.")
                sys.exit(1)

            console.print("\n[bold]Modo interactivo[/bold]")
            console.print("Para cada endpoint, puedes aceptar la sugerencia, modificarla o saltar.\n")

            for i, ep in enumerate(initial_score.incomplete_endpoints, 1):
                console.print(f"\n[bold]Endpoint {i}/{len(initial_score.incomplete_endpoints)}[/bold]")
                console.print(f"  [cyan]{ep.method.upper()}[/cyan] {ep.path}")
                console.print(f"  Falta: {', '.join(ep.missing_fields)}")

                enrichment = EnrichmentData(method=ep.method, path=ep.path)

                # Descripción
                if "description" in ep.missing_fields:
                    suggested = ep.suggested_values.get("description", "")
                    console.print(f"\n  Sugerencia: [dim]{suggested}[/dim]")

                    action = questionary.select(
                        "¿Descripción?",
                        choices=["Usar sugerencia", "Escribir otra", "Saltar"]
                    ).ask()

                    if action == "Usar sugerencia":
                        enrichment.description = suggested
                    elif action == "Escribir otra":
                        custom = questionary.text("Tu descripción:").ask()
                        if custom:
                            enrichment.description = custom

                # OperationId
                if "operationId" in ep.missing_fields:
                    suggested = ep.suggested_values.get("operationId", "")
                    console.print(f"\n  Sugerencia operationId: [dim]{suggested}[/dim]")

                    action = questionary.select(
                        "¿Operation ID?",
                        choices=["Usar sugerencia", "Escribir otro", "Saltar"]
                    ).ask()

                    if action == "Usar sugerencia":
                        enrichment.operation_id = suggested
                    elif action == "Escribir otro":
                        custom = questionary.text("Tu operationId:").ask()
                        if custom:
                            enrichment.operation_id = custom

                # Tags
                if "tags" in ep.missing_fields:
                    suggested_tags = ep.suggested_values.get("tags", [])
                    if suggested_tags:
                        console.print(f"\n  Tags sugeridos: [dim]{', '.join(suggested_tags)}[/dim]")

                        action = questionary.select(
                            "¿Tags?",
                            choices=["Usar sugeridos", "Escribir otros", "Saltar"]
                        ).ask()

                        if action == "Usar sugeridos":
                            enrichment.tags = suggested_tags
                        elif action == "Escribir otros":
                            custom = questionary.text("Tags (separados por coma):").ask()
                            if custom:
                                enrichment.tags = [t.strip() for t in custom.split(",") if t.strip()]

                # Agregar si hay cambios
                if enrichment.description or enrichment.operation_id or enrichment.tags:
                    enrichments.append(enrichment)

        if not enrichments:
            console.print("\n[yellow]No se aplicaron cambios.[/yellow]")
            return

        # Aplicar enrichments
        enriched_spec = scorer.apply_enrichment(raw_spec, enrichments)

        # Calcular nuevo score
        new_score = scorer.calculate_score(enriched_spec)

        console.print(f"\n[bold]Resultado:[/bold]")
        console.print(f"  Score anterior: {initial_score.overall_score}/100")
        console.print(f"  Score nuevo: [green]{new_score.overall_score}/100[/green] (+{new_score.overall_score - initial_score.overall_score})")
        console.print(f"  Cambios aplicados: {len(enrichments)}")

        # Guardar archivo
        if not output:
            # Generar nombre automático
            from pathlib import Path
            p = Path(spec_path)
            output = str(p.parent / f"{p.stem}_enriched{p.suffix}")

        with open(output, "w", encoding="utf-8") as f:
            if is_json or output.endswith(".json"):
                json.dump(enriched_spec, f, indent=2, ensure_ascii=False)
            else:
                yaml.dump(enriched_spec, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

        console.print(f"\n[green]✓[/green] Especificación enriquecida guardada en: {output}")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


@cli.command()
@click.argument("config_path", type=click.Path(exists=True))
@click.option(
    "--parallel/--no-parallel",
    default=True,
    help="Ejecutar generaciones en paralelo"
)
@click.option(
    "--workers", "-w",
    type=int,
    default=None,
    help="Numero de workers para ejecucion paralela"
)
def batch(config_path: str, parallel: bool, workers: int | None):
    """
    Genera multiples servidores MCP desde archivo de configuracion.

    CONFIG_PATH: Ruta al archivo YAML de configuracion batch.

    Ejemplo de configuracion (batch.yaml):

    \b
    output_dir: ./output
    framework: fastmcp

    specs:
      - path: ./specs/petstore.yaml
        service_name: petstore

      - path: ./specs/github.yaml
        service_name: github
        framework: typescript
    """
    from .batch import run_batch, generate_batch_report

    console.print(Panel.fit(
        "[bold blue]OpenAPI to MCP[/bold blue] - Batch Generation",
        border_style="blue"
    ))

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Procesando specs...", total=None)

            summary = run_batch(config_path, parallel=parallel, max_workers=workers)

            progress.update(task, completed=True)

        # Mostrar resultados
        report = generate_batch_report(summary)
        console.print(report)

        # Resumen final
        if summary.failed > 0:
            console.print(f"\n[yellow]Completado con {summary.failed} errores[/yellow]")
            sys.exit(1)
        else:
            console.print(f"\n[green]Todos los {summary.successful} specs procesados exitosamente[/green]")

    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        sys.exit(1)


def main():
    """Punto de entrada principal."""
    cli()


if __name__ == "__main__":
    main()
