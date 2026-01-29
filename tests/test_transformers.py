"""
Tests para los transformadores de Tools y Resources.
"""

import pytest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from openapi_to_mcp.parsers.openapi_parser import OpenAPIParser
from openapi_to_mcp.transformers.tool_transformer import ToolTransformer
from openapi_to_mcp.transformers.resource_transformer import ResourceTransformer
from openapi_to_mcp.models import MCPTool, MCPResource, HttpMethod


class TestToolTransformer:
    """Tests para ToolTransformer."""

    @pytest.fixture
    def sample_spec(self):
        """Spec de ejemplo parseada."""
        parser = OpenAPIParser(strict_validation=False)
        return parser.parse_from_string("""
openapi: "3.0.3"
info:
  title: Test API
  version: "1.0.0"
paths:
  /users:
    get:
      operationId: listUsers
      summary: List all users
      description: Returns a paginated list of users
      tags:
        - Users
      parameters:
        - name: page
          in: query
          description: Page number
          schema:
            type: integer
            default: 0
        - name: size
          in: query
          description: Page size
          schema:
            type: integer
            default: 20
      responses:
        "200":
          description: Success
          content:
            application/json:
              schema:
                type: array
                items:
                  type: object
    post:
      operationId: createUser
      summary: Create a new user
      tags:
        - Users
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                name:
                  type: string
                email:
                  type: string
              required:
                - name
                - email
      responses:
        "201":
          description: Created
  /users/{userId}:
    get:
      operationId: getUserById
      summary: Get user by ID
      tags:
        - Users
      parameters:
        - name: userId
          in: path
          required: true
          description: User unique identifier
          schema:
            type: string
            format: uuid
      responses:
        "200":
          description: Success
    delete:
      operationId: deleteUser
      summary: Delete user
      deprecated: true
      tags:
        - Users
      parameters:
        - name: userId
          in: path
          required: true
          schema:
            type: string
      responses:
        "204":
          description: Deleted
components:
  schemas:
    User:
      type: object
      properties:
        id:
          type: string
        name:
          type: string
""")

    @pytest.fixture
    def transformer(self):
        """Transformer con prefijo de prueba."""
        return ToolTransformer(service_prefix="test_api")

    def test_transform_creates_tools(self, transformer, sample_spec):
        """Test que transform crea tools."""
        tools = transformer.transform(sample_spec)

        assert len(tools) > 0
        assert all(isinstance(t, MCPTool) for t in tools)

    def test_tool_naming_with_operation_id(self, transformer, sample_spec):
        """Test naming usando operationId."""
        tools = transformer.transform(sample_spec)

        # Buscar tool de listUsers
        list_tool = next(t for t in tools if "list_users" in t.name.lower())
        assert list_tool.operation_id == "listUsers"
        assert list_tool.name.startswith("test_api_")

    def test_tool_http_method(self, transformer, sample_spec):
        """Test que el método HTTP se extrae correctamente."""
        tools = transformer.transform(sample_spec)

        get_tools = [t for t in tools if t.http_method == HttpMethod.GET]
        post_tools = [t for t in tools if t.http_method == HttpMethod.POST]

        assert len(get_tools) >= 2  # listUsers y getUserById
        assert len(post_tools) >= 1  # createUser

    def test_tool_parameters_extraction(self, transformer, sample_spec):
        """Test extracción de parámetros."""
        tools = transformer.transform(sample_spec)

        # Tool listUsers debe tener params page y size
        list_tool = next(t for t in tools if "list_users" in t.name.lower())
        param_names = [p.name for p in list_tool.parameters]

        assert "page" in param_names
        assert "size" in param_names

    def test_path_parameter_marked_required(self, transformer, sample_spec):
        """Test que parámetros de path son requeridos."""
        tools = transformer.transform(sample_spec)

        # Tool getUserById tiene userId como path param
        get_by_id = next(t for t in tools if "get_user_by_id" in t.name.lower())
        user_id_param = next(p for p in get_by_id.parameters if p.name == "userId")

        assert user_id_param.required is True

    def test_request_body_schema_extracted(self, transformer, sample_spec):
        """Test que request body se extrae."""
        tools = transformer.transform(sample_spec)

        create_tool = next(t for t in tools if "create_user" in t.name.lower())

        assert create_tool.request_body_schema is not None
        assert create_tool.request_body_schema["required"] is True

    def test_deprecated_excluded_by_default(self, transformer, sample_spec):
        """Test que operaciones deprecated se excluyen."""
        tools = transformer.transform(sample_spec)

        # deleteUser está deprecated
        delete_tools = [t for t in tools if "delete" in t.name.lower()]
        assert len(delete_tools) == 0

    def test_deprecated_included_when_enabled(self, sample_spec):
        """Test que deprecated se incluye cuando se habilita."""
        transformer = ToolTransformer(
            service_prefix="test",
            include_deprecated=True
        )
        tools = transformer.transform(sample_spec)

        delete_tools = [t for t in tools if "delete" in t.name.lower()]
        assert len(delete_tools) == 1
        assert delete_tools[0].deprecated is True

    def test_tool_tags_preserved(self, transformer, sample_spec):
        """Test que tags se preservan."""
        tools = transformer.transform(sample_spec)

        for tool in tools:
            assert "Users" in tool.tags

    def test_input_schema_generation(self, transformer, sample_spec):
        """Test generación de input schema."""
        tools = transformer.transform(sample_spec)

        list_tool = next(t for t in tools if "list_users" in t.name.lower())
        schema = list_tool.get_input_schema()

        assert schema["type"] == "object"
        assert "properties" in schema
        assert "page" in schema["properties"]
        assert schema["properties"]["page"]["type"] == "integer"

    def test_unique_tool_names(self, transformer, sample_spec):
        """Test que nombres de tools son únicos."""
        tools = transformer.transform(sample_spec)
        names = [t.name for t in tools]

        assert len(names) == len(set(names))


class TestResourceTransformer:
    """Tests para ResourceTransformer."""

    @pytest.fixture
    def sample_spec(self):
        """Spec de ejemplo."""
        parser = OpenAPIParser(strict_validation=False)
        return parser.parse_from_string("""
openapi: "3.0.3"
info:
  title: Test API
  version: "1.0.0"
  description: API for testing
paths:
  /users:
    get:
      operationId: listUsers
      responses:
        "200":
          description: Success
  /users/{id}:
    get:
      operationId: getUserById
      parameters:
        - name: id
          in: path
          required: true
          schema:
            type: string
      responses:
        "200":
          description: Success
components:
  schemas:
    User:
      type: object
      description: User entity
      properties:
        id:
          type: string
        name:
          type: string
        email:
          type: string
          format: email
    UserList:
      type: array
      items:
        $ref: "#/components/schemas/User"
    _InternalSchema:
      type: object
      description: Internal use only
""")

    @pytest.fixture
    def sample_tools(self, sample_spec):
        """Tools de ejemplo."""
        transformer = ToolTransformer(service_prefix="test")
        return transformer.transform(sample_spec)

    @pytest.fixture
    def transformer(self):
        """Resource transformer."""
        return ResourceTransformer(service_prefix="test")

    def test_transform_creates_resources(self, transformer, sample_spec, sample_tools):
        """Test que transform crea resources."""
        resources = transformer.transform(sample_spec, sample_tools)

        assert len(resources) > 0
        assert all(isinstance(r, MCPResource) for r in resources)

    def test_schema_resources_created(self, transformer, sample_spec, sample_tools):
        """Test que se crean resources para schemas."""
        resources = transformer.transform(sample_spec, sample_tools)

        schema_resources = [r for r in resources if "schemas" in r.uri]
        assert len(schema_resources) >= 2  # User y UserList

    def test_internal_schemas_excluded(self, transformer, sample_spec, sample_tools):
        """Test que schemas internos se excluyen."""
        resources = transformer.transform(sample_spec, sample_tools)

        internal = [r for r in resources if "internal" in r.uri.lower()]
        assert len(internal) == 0

    def test_internal_schemas_included_when_enabled(self, sample_spec, sample_tools):
        """Test inclusión de schemas internos."""
        transformer = ResourceTransformer(
            service_prefix="test",
            include_internal_schemas=True
        )
        resources = transformer.transform(sample_spec, sample_tools)

        internal = [r for r in resources if "internal" in r.uri.lower()]
        assert len(internal) == 1

    def test_api_documentation_resource(self, transformer, sample_spec, sample_tools):
        """Test que se crea resource de documentación."""
        resources = transformer.transform(sample_spec, sample_tools)

        doc_resources = [r for r in resources if "documentation" in r.uri]
        assert len(doc_resources) == 1
        assert "Test API" in doc_resources[0].description

    def test_entity_resources_for_get_endpoints(self, transformer, sample_spec, sample_tools):
        """Test resources para endpoints GET."""
        resources = transformer.transform(sample_spec, sample_tools)

        entity_resources = [r for r in resources if "entities" in r.uri]
        # /users debería generar un entity resource
        assert len(entity_resources) >= 1

    def test_collection_detection(self, transformer, sample_spec, sample_tools):
        """Test detección de colecciones."""
        resources = transformer.transform(sample_spec, sample_tools)

        # UserList es un array, debería marcarse como colección
        user_list = next(
            (r for r in resources if "user_list" in r.uri.lower()),
            None
        )
        if user_list:
            assert user_list.is_collection is True

    def test_resource_uri_format(self, transformer, sample_spec, sample_tools):
        """Test formato de URIs."""
        resources = transformer.transform(sample_spec, sample_tools)

        for resource in resources:
            assert resource.uri.startswith("test://")
            assert " " not in resource.uri  # Sin espacios

    def test_unique_resource_uris(self, transformer, sample_spec, sample_tools):
        """Test que URIs son únicas."""
        resources = transformer.transform(sample_spec, sample_tools)
        uris = [r.uri for r in resources]

        assert len(uris) == len(set(uris))

    def test_schema_description_generated(self, transformer, sample_spec, sample_tools):
        """Test generación de descripciones para schemas."""
        resources = transformer.transform(sample_spec, sample_tools)

        user_resource = next(
            r for r in resources
            if "schemas" in r.uri and "user" in r.uri.lower() and "list" not in r.uri.lower()
        )

        # Debe incluir descripción del schema
        assert "User entity" in user_resource.description or "object" in user_resource.description

    def test_resources_summary(self, transformer, sample_spec, sample_tools):
        """Test generación de resumen."""
        resources = transformer.transform(sample_spec, sample_tools)
        summary = transformer.get_resources_summary(resources)

        assert "total" in summary
        assert "schemas" in summary
        assert summary["total"] == len(resources)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
