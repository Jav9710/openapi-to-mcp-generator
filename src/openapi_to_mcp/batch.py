"""
Procesador de generacion batch.

Permite generar multiples servidores MCP a partir de un archivo
de configuracion YAML con multiples specs y opciones.
"""

import concurrent.futures
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .endpoint_selector import EndpointSelector
from .generators.server_generator import MCPServerGenerator
from .models import EndpointFilter, MCPFramework, MCPServerConfig
from .parsers.openapi_parser import OpenAPIParser
from .transformers.resource_transformer import ResourceTransformer
from .transformers.tool_transformer import ToolTransformer

logger = logging.getLogger(__name__)


@dataclass
class BatchSpec:
    """Configuracion de un spec en batch."""
    path: str
    service_name: str
    output_dir: str | None = None
    framework: str = "fastmcp"
    base_url: str | None = None
    include_patterns: list[str] = field(default_factory=list)
    exclude_patterns: list[str] = field(default_factory=list)
    selected_endpoints: list[str] = field(default_factory=list)


@dataclass
class BatchResult:
    """Resultado de generacion de un spec."""
    service_name: str
    success: bool
    output_path: str | None = None
    tools_count: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class BatchSummary:
    """Resumen de ejecucion batch."""
    total: int
    successful: int
    failed: int
    results: list[BatchResult] = field(default_factory=list)


def load_batch_config(config_path: str | Path) -> list[BatchSpec]:
    """
    Carga configuracion batch desde archivo YAML.

    Args:
        config_path: Ruta al archivo de configuracion

    Returns:
        Lista de BatchSpec con configuracion de cada generacion

    Example YAML:
        output_dir: ./output
        framework: fastmcp

        specs:
          - path: ./specs/petstore.yaml
            service_name: petstore
            base_url: https://petstore.swagger.io/v2

          - path: ./specs/github.yaml
            service_name: github
            framework: typescript
            include_patterns:
              - /repos/*
              - /users/*
    """
    config_path = Path(config_path)

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    default_output = config.get("output_dir", "./output")
    default_framework = config.get("framework", "fastmcp")

    specs = []
    for spec_config in config.get("specs", []):
        specs.append(BatchSpec(
            path=spec_config["path"],
            service_name=spec_config["service_name"],
            output_dir=spec_config.get("output_dir", default_output),
            framework=spec_config.get("framework", default_framework),
            base_url=spec_config.get("base_url"),
            include_patterns=spec_config.get("include_patterns", []),
            exclude_patterns=spec_config.get("exclude_patterns", []),
            selected_endpoints=spec_config.get("selected_endpoints", []),
        ))

    return specs


def process_single_spec(spec_config: BatchSpec) -> BatchResult:
    """
    Procesa un solo spec y genera el servidor MCP.

    Args:
        spec_config: Configuracion del spec

    Returns:
        BatchResult con resultado de la generacion
    """
    errors = []
    warnings = []

    try:
        # Parsear spec
        parser = OpenAPIParser(strict_validation=False)
        spec = parser.parse(spec_config.path)

        # Crear filtro de endpoints
        selector = EndpointSelector(spec, include_deprecated=True)

        if spec_config.selected_endpoints:
            endpoint_filter = EndpointFilter(selected_endpoints=spec_config.selected_endpoints)
        elif spec_config.include_patterns or spec_config.exclude_patterns:
            endpoints = selector.filter_by_patterns(
                spec_config.include_patterns,
                spec_config.exclude_patterns,
            )
            endpoint_filter = EndpointFilter(
                selected_endpoints=[f"{e.method}:{e.path}" for e in endpoints]
            )
        else:
            # Todos los endpoints
            all_eps = selector.get_all_endpoints()
            endpoint_filter = EndpointFilter(
                selected_endpoints=[f"{e.method}:{e.path}" for e in all_eps]
            )

        # Configurar framework
        framework_map = {
            "fastmcp": MCPFramework.FASTMCP,
            "mcp": MCPFramework.MCP,
            "typescript": MCPFramework.TYPESCRIPT,
        }
        framework = framework_map.get(spec_config.framework, MCPFramework.FASTMCP)

        base_url = spec_config.base_url or spec.get_base_url()

        config = MCPServerConfig(
            service_name=spec_config.service_name,
            service_prefix=spec_config.service_name,
            base_url=base_url,
            mcp_framework=framework,
        )

        # Transformar
        tool_transformer = ToolTransformer(service_prefix=spec_config.service_name)
        tools = tool_transformer.transform(spec, endpoint_filter=endpoint_filter)

        resource_transformer = ResourceTransformer(service_prefix=spec_config.service_name)
        resources = resource_transformer.transform(spec, tools)

        # Generar
        output_dir = spec_config.output_dir or "./output"
        generator = MCPServerGenerator(output_dir=output_dir)
        result = generator.generate(spec=spec, tools=tools, resources=resources, config=config)

        return BatchResult(
            service_name=spec_config.service_name,
            success=result.success,
            output_path=result.output_path,
            tools_count=len(result.tools_generated),
            errors=result.errors,
            warnings=result.warnings,
        )

    except Exception as e:
        logger.error(f"Error processing {spec_config.service_name}: {e}")
        errors.append(str(e))
        return BatchResult(
            service_name=spec_config.service_name,
            success=False,
            errors=errors,
        )


def run_batch(
    config_path: str | Path,
    parallel: bool = True,
    max_workers: int | None = None,
) -> BatchSummary:
    """
    Ejecuta generacion batch de multiples specs.

    Args:
        config_path: Ruta al archivo de configuracion YAML
        parallel: Si True, procesa specs en paralelo
        max_workers: Numero maximo de workers para ejecucion paralela

    Returns:
        BatchSummary con resultados consolidados
    """
    specs = load_batch_config(config_path)
    results = []

    if parallel and len(specs) > 1:
        workers = max_workers or min(len(specs), os.cpu_count() or 4)
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(process_single_spec, s): s for s in specs}
            for future in concurrent.futures.as_completed(futures):
                results.append(future.result())
    else:
        for spec_config in specs:
            results.append(process_single_spec(spec_config))

    successful = sum(1 for r in results if r.success)
    failed = sum(1 for r in results if not r.success)

    return BatchSummary(
        total=len(results),
        successful=successful,
        failed=failed,
        results=results,
    )


def generate_batch_report(summary: BatchSummary) -> str:
    """
    Genera reporte de ejecucion batch en formato texto.

    Args:
        summary: Resumen de ejecucion batch

    Returns:
        Reporte formateado como string
    """
    lines = [
        "=" * 60,
        "BATCH GENERATION REPORT",
        "=" * 60,
        "",
        f"Total specs processed: {summary.total}",
        f"Successful: {summary.successful}",
        f"Failed: {summary.failed}",
        "",
        "-" * 60,
    ]

    for result in summary.results:
        status = "OK" if result.success else "FAILED"
        lines.append(f"\n[{status}] {result.service_name}")
        if result.output_path:
            lines.append(f"    Output: {result.output_path}")
        if result.tools_count:
            lines.append(f"    Tools: {result.tools_count}")
        if result.errors:
            for err in result.errors:
                lines.append(f"    Error: {err}")
        if result.warnings:
            for warn in result.warnings:
                lines.append(f"    Warning: {warn}")

    lines.extend(["", "=" * 60])
    return "\n".join(lines)
