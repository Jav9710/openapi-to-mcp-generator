# MCP Server Templates

This directory contains Jinja2 templates for generating MCP servers.

## Structure

```
templates/
├── fastmcp/          # FastMCP Python templates
│   ├── server.py.j2
│   ├── http_client.py.j2
│   └── config.py.j2
├── mcp/              # Standard MCP Python templates
│   ├── server.py.j2
│   └── ...
└── typescript/       # TypeScript templates
    ├── index.ts.j2
    └── ...
```

## Using Custom Templates

You can override these templates by specifying a custom templates directory:

```python
from openapi_to_mcp.generators.server_generator import MCPServerGenerator

generator = MCPServerGenerator(
    output_dir="./output",
    templates_dir="./my-custom-templates"
)
```

## Template Variables

### Common Variables

- `service_name`: Name of the MCP service
- `spec_title`: OpenAPI spec title
- `spec_version`: OpenAPI spec version
- `base_url`: Base URL for API calls
- `timeout`: Default request timeout

### Tool Variables

Each tool in `tools` list has:
- `name`: Tool name
- `function_name`: Python/TypeScript function name
- `description`: Tool description
- `method`: HTTP method (GET, POST, etc.)
- `path`: API path
- `parameters`: List of parameters
- `path_params`: Path parameters only
- `query_params`: Query parameters only
- `has_body`: Whether tool has request body

### Parameter Variables

Each parameter has:
- `name`: Parameter name
- `python_type`: Python type annotation
- `description`: Parameter description
- `required`: Whether required
- `has_default`: Whether has default value
- `default_value`: Default value if any
