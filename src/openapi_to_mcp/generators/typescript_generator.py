"""
Generador de servidor MCP en TypeScript.

Genera un servidor MCP usando @modelcontextprotocol/sdk para Node.js.
"""

import json
from dataclasses import dataclass
from pathlib import Path

from ..models import MCPTool, MCPResource, MCPServerConfig, ParameterLocation
from ..parsers.openapi_parser import OpenAPISpec


@dataclass
class TypeScriptGeneratorResult:
    """Resultado de la generacion TypeScript."""
    success: bool
    output_path: str
    files_generated: list[str]
    errors: list[str]


class TypeScriptGenerator:
    """Genera servidores MCP en TypeScript."""

    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)

    def generate(
        self,
        spec: OpenAPISpec,
        tools: list[MCPTool],
        resources: list[MCPResource],
        config: MCPServerConfig,
    ) -> TypeScriptGeneratorResult:
        """
        Genera el servidor MCP en TypeScript.

        Returns:
            TypeScriptGeneratorResult con archivos generados
        """
        errors = []
        files_generated = []

        try:
            # Crear directorio de salida
            service_dir = self.output_dir / config.service_name
            service_dir.mkdir(parents=True, exist_ok=True)
            src_dir = service_dir / "src"
            src_dir.mkdir(exist_ok=True)

            # package.json
            pkg_content = self._generate_package_json(config, spec)
            (service_dir / "package.json").write_text(pkg_content, encoding="utf-8")
            files_generated.append("package.json")

            # tsconfig.json
            tsconfig = self._generate_tsconfig()
            (service_dir / "tsconfig.json").write_text(tsconfig, encoding="utf-8")
            files_generated.append("tsconfig.json")

            # src/index.ts
            index_content = self._generate_index(config, spec, tools, resources)
            (src_dir / "index.ts").write_text(index_content, encoding="utf-8")
            files_generated.append("src/index.ts")

            # src/tools.ts
            tools_content = self._generate_tools(tools, config)
            (src_dir / "tools.ts").write_text(tools_content, encoding="utf-8")
            files_generated.append("src/tools.ts")

            # src/http-client.ts
            client_content = self._generate_http_client(config)
            (src_dir / "http-client.ts").write_text(client_content, encoding="utf-8")
            files_generated.append("src/http-client.ts")

            # src/types.ts
            types_content = self._generate_types(tools)
            (src_dir / "types.ts").write_text(types_content, encoding="utf-8")
            files_generated.append("src/types.ts")

            # .env.example
            env_content = self._generate_env_example(config)
            (service_dir / ".env.example").write_text(env_content, encoding="utf-8")
            files_generated.append(".env.example")

            return TypeScriptGeneratorResult(
                success=True,
                output_path=str(service_dir),
                files_generated=files_generated,
                errors=errors,
            )

        except Exception as e:
            errors.append(str(e))
            return TypeScriptGeneratorResult(
                success=False,
                output_path=str(self.output_dir / config.service_name),
                files_generated=files_generated,
                errors=errors,
            )

    def _generate_package_json(self, config: MCPServerConfig, spec: OpenAPISpec) -> str:
        """Genera package.json."""
        pkg = {
            "name": f"mcp-server-{config.service_name}",
            "version": spec.version or "1.0.0",
            "description": f"MCP Server for {spec.title or config.service_name}",
            "type": "module",
            "main": "dist/index.js",
            "scripts": {
                "build": "tsc",
                "start": "node dist/index.js",
                "dev": "ts-node src/index.ts"
            },
            "dependencies": {
                "@modelcontextprotocol/sdk": "^1.0.0",
                "axios": "^1.6.0",
                "dotenv": "^16.3.0"
            },
            "devDependencies": {
                "@types/node": "^20.0.0",
                "typescript": "^5.3.0",
                "ts-node": "^10.9.0"
            }
        }
        return json.dumps(pkg, indent=2)

    def _generate_tsconfig(self) -> str:
        """Genera tsconfig.json."""
        tsconfig = {
            "compilerOptions": {
                "target": "ES2022",
                "module": "NodeNext",
                "moduleResolution": "NodeNext",
                "outDir": "./dist",
                "rootDir": "./src",
                "strict": True,
                "esModuleInterop": True,
                "skipLibCheck": True,
                "forceConsistentCasingInFileNames": True,
                "declaration": True
            },
            "include": ["src/**/*"],
            "exclude": ["node_modules", "dist"]
        }
        return json.dumps(tsconfig, indent=2)

    def _generate_index(
        self,
        config: MCPServerConfig,
        spec: OpenAPISpec,
        tools: list[MCPTool],
        resources: list[MCPResource],
    ) -> str:
        """Genera src/index.ts."""
        tool_imports = ", ".join([self._to_camel_case(t.name) for t in tools])

        return f'''import {{ Server }} from "@modelcontextprotocol/sdk/server/index.js";
import {{ StdioServerTransport }} from "@modelcontextprotocol/sdk/server/stdio.js";
import {{
  CallToolRequestSchema,
  ListToolsRequestSchema,
}} from "@modelcontextprotocol/sdk/types.js";
import "dotenv/config";

import {{ {tool_imports} }} from "./tools.js";
import {{ toolDefinitions }} from "./types.js";

const server = new Server(
  {{
    name: "{config.service_name}",
    version: "{spec.version or '1.0.0'}",
  }},
  {{
    capabilities: {{
      tools: {{}},
    }},
  }}
);

// List available tools
server.setRequestHandler(ListToolsRequestSchema, async () => {{
  return {{ tools: toolDefinitions }};
}});

// Handle tool calls
server.setRequestHandler(CallToolRequestSchema, async (request) => {{
  const {{ name, arguments: args }} = request.params;

  try {{
    let result: unknown;

    switch (name) {{
{self._generate_tool_switch_cases(tools)}
      default:
        throw new Error(`Unknown tool: ${{name}}`);
    }}

    return {{
      content: [
        {{
          type: "text",
          text: typeof result === "string" ? result : JSON.stringify(result, null, 2),
        }},
      ],
    }};
  }} catch (error) {{
    const errorMessage = error instanceof Error ? error.message : String(error);
    return {{
      content: [{{ type: "text", text: `Error: ${{errorMessage}}` }}],
      isError: true,
    }};
  }}
}});

async function main() {{
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("{config.service_name} MCP Server running on stdio");
}}

main().catch(console.error);
'''

    def _generate_tool_switch_cases(self, tools: list[MCPTool]) -> str:
        """Genera los case del switch para cada tool."""
        cases = []
        for tool in tools:
            fn_name = self._to_camel_case(tool.name)
            cases.append(f'      case "{tool.name}":\n        result = await {fn_name}(args as any);\n        break;')
        return "\n".join(cases)

    def _generate_tools(self, tools: list[MCPTool], config: MCPServerConfig) -> str:
        """Genera src/tools.ts."""
        functions = []

        for tool in tools:
            fn_name = self._to_camel_case(tool.name)
            params = self._generate_tool_params_type(tool)
            body = self._generate_tool_body(tool, config)

            func = f'''
/**
 * {tool.description}
 */
export async function {fn_name}(params: {params}): Promise<unknown> {{
{body}
}}
'''
            functions.append(func)

        return f'''import {{ httpClient }} from "./http-client.js";

{"".join(functions)}
'''

    def _generate_tool_params_type(self, tool: MCPTool) -> str:
        """Genera el tipo de parametros para un tool."""
        if not tool.parameters:
            return "Record<string, never>"

        props = []
        for param in tool.parameters:
            ts_type = self._openapi_type_to_ts(param.schema.get("type", "string"))
            optional = "?" if not param.required else ""
            props.append(f"{param.name}{optional}: {ts_type}")

        return "{ " + "; ".join(props) + " }"

    def _generate_tool_body(self, tool: MCPTool, config: MCPServerConfig) -> str:
        """Genera el body de la funcion del tool."""
        method = tool.method.lower()
        path = tool.path

        # Separar parametros por ubicacion
        path_params = [p for p in tool.parameters if p.location == ParameterLocation.PATH]
        query_params = [p for p in tool.parameters if p.location == ParameterLocation.QUERY]
        has_body = tool.request_body is not None

        lines = []

        # Construir URL con path params
        if path_params:
            lines.append(f'  let url = `{path}`;')
            for pp in path_params:
                lines.append(f'  url = url.replace("{{{pp.name}}}", String(params.{pp.name}));')
        else:
            lines.append(f'  const url = "{path}";')

        # Query params
        if query_params:
            qp_names = [f'"{qp.name}": params.{qp.name}' for qp in query_params]
            lines.append(f'  const queryParams = {{ {", ".join(qp_names)} }};')
        else:
            lines.append('  const queryParams = {};')

        # Request body
        if has_body:
            # Asumir que hay un param 'body' o usar todos los no-path/query
            lines.append('  const body = params.body ?? params;')
        else:
            lines.append('  const body = undefined;')

        # HTTP call
        lines.append(f'  return await httpClient.request("{method.upper()}", url, queryParams, body);')

        return "\n".join(lines)

    def _generate_http_client(self, config: MCPServerConfig) -> str:
        """Genera src/http-client.ts."""
        return f'''import axios, {{ AxiosInstance }} from "axios";

class HttpClient {{
  private client: AxiosInstance;

  constructor() {{
    this.client = axios.create({{
      baseURL: process.env.API_BASE_URL || "{config.base_url}",
      headers: {{
        "Content-Type": "application/json",
        ...(process.env.API_KEY && {{ "Authorization": `Bearer ${{process.env.API_KEY}}` }}),
      }},
      timeout: 30000,
    }});
  }}

  async request(
    method: string,
    path: string,
    queryParams: Record<string, unknown> = {{}},
    body?: unknown
  ): Promise<unknown> {{
    const response = await this.client.request({{
      method,
      url: path,
      params: queryParams,
      data: body,
    }});
    return response.data;
  }}
}}

export const httpClient = new HttpClient();
'''

    def _generate_types(self, tools: list[MCPTool]) -> str:
        """Genera src/types.ts con las definiciones de tools."""
        definitions = []

        for tool in tools:
            props = {}
            required = []

            for param in tool.parameters:
                props[param.name] = {
                    "type": param.schema.get("type", "string"),
                    "description": param.description or "",
                }
                if param.required:
                    required.append(param.name)

            tool_def = {
                "name": tool.name,
                "description": tool.description,
                "inputSchema": {
                    "type": "object",
                    "properties": props,
                    "required": required,
                },
            }
            definitions.append(tool_def)

        return f'''export const toolDefinitions = {json.dumps(definitions, indent=2)};
'''

    def _generate_env_example(self, config: MCPServerConfig) -> str:
        """Genera .env.example."""
        return f'''# Base URL for the API
API_BASE_URL={config.base_url}

# API Key (if required)
API_KEY=your_api_key_here
'''

    def _to_camel_case(self, name: str) -> str:
        """Convierte snake_case a camelCase."""
        parts = name.replace("-", "_").split("_")
        return parts[0] + "".join(p.capitalize() for p in parts[1:])

    def _openapi_type_to_ts(self, openapi_type: str) -> str:
        """Mapea tipos OpenAPI a TypeScript."""
        mapping = {
            "string": "string",
            "integer": "number",
            "number": "number",
            "boolean": "boolean",
            "array": "unknown[]",
            "object": "Record<string, unknown>",
        }
        return mapping.get(openapi_type, "unknown")
