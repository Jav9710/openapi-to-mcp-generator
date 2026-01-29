"""
Tests para el parser de OpenAPI.
"""

import pytest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from openapi_to_mcp.parsers.openapi_parser import OpenAPIParser, OpenAPIParserError
from openapi_to_mcp.models import OpenAPISpec


class TestOpenAPIParser:
    """Tests para OpenAPIParser."""

    @pytest.fixture
    def parser(self):
        """Parser con validación deshabilitada para tests."""
        return OpenAPIParser(strict_validation=False)

    @pytest.fixture
    def sample_spec_content(self):
        """Contenido de spec OpenAPI mínimo."""
        return """
openapi: "3.0.3"
info:
  title: Test API
  version: "1.0.0"
  description: API de prueba
servers:
  - url: https://api.example.com/v1
    description: Production
paths:
  /users:
    get:
      operationId: listUsers
      summary: List all users
      parameters:
        - name: page
          in: query
          schema:
            type: integer
      responses:
        "200":
          description: Success
    post:
      operationId: createUser
      summary: Create user
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                name:
                  type: string
      responses:
        "201":
          description: Created
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
      properties:
        id:
          type: string
        name:
          type: string
  securitySchemes:
    BearerAuth:
      type: http
      scheme: bearer
"""

    def test_parse_from_string(self, parser, sample_spec_content):
        """Test parsing desde string."""
        spec = parser.parse_from_string(sample_spec_content)

        assert isinstance(spec, OpenAPISpec)
        assert spec.title == "Test API"
        assert spec.version == "1.0.0"
        assert spec.openapi_version == "3.0.3"

    def test_extract_paths(self, parser, sample_spec_content):
        """Test extracción de paths."""
        spec = parser.parse_from_string(sample_spec_content)

        assert "/users" in spec.paths
        assert "/users/{id}" in spec.paths
        assert "get" in spec.paths["/users"]
        assert "post" in spec.paths["/users"]

    def test_extract_operations(self, parser, sample_spec_content):
        """Test extracción de operaciones."""
        spec = parser.parse_from_string(sample_spec_content)

        get_users = spec.paths["/users"]["get"]
        assert get_users["operationId"] == "listUsers"
        assert get_users["summary"] == "List all users"

    def test_extract_parameters(self, parser, sample_spec_content):
        """Test extracción de parámetros."""
        spec = parser.parse_from_string(sample_spec_content)

        get_users = spec.paths["/users"]["get"]
        params = get_users["parameters"]
        assert len(params) == 1
        assert params[0]["name"] == "page"
        assert params[0]["in"] == "query"

    def test_extract_schemas(self, parser, sample_spec_content):
        """Test extracción de schemas."""
        spec = parser.parse_from_string(sample_spec_content)

        assert "User" in spec.components_schemas
        user_schema = spec.components_schemas["User"]
        assert user_schema["type"] == "object"
        assert "id" in user_schema["properties"]

    def test_extract_security_schemes(self, parser, sample_spec_content):
        """Test extracción de security schemes."""
        spec = parser.parse_from_string(sample_spec_content)

        assert "BearerAuth" in spec.security_schemes
        bearer = spec.security_schemes["BearerAuth"]
        assert bearer.scheme == "bearer"

    def test_operation_count(self, parser, sample_spec_content):
        """Test conteo de operaciones."""
        spec = parser.parse_from_string(sample_spec_content)
        count = parser.get_operation_count(spec)

        # GET /users, POST /users, GET /users/{id}
        assert count == 3

    def test_get_base_url(self, parser, sample_spec_content):
        """Test obtención de URL base."""
        spec = parser.parse_from_string(sample_spec_content)
        url = spec.get_base_url()

        assert url == "https://api.example.com/v1"

    def test_invalid_version_raises_error(self, parser):
        """Test que versión inválida lanza error."""
        invalid_spec = """
swagger: "2.0"
info:
  title: Test
  version: "1.0"
paths: {}
"""
        with pytest.raises(OpenAPIParserError):
            parser.parse_from_string(invalid_spec)

    def test_missing_openapi_field_raises_error(self, parser):
        """Test que spec sin campo openapi lanza error."""
        invalid_spec = """
info:
  title: Test
  version: "1.0"
paths: {}
"""
        with pytest.raises(OpenAPIParserError):
            parser.parse_from_string(invalid_spec)


class TestOpenAPIParserRefs:
    """Tests para resolución de referencias."""

    @pytest.fixture
    def parser(self):
        return OpenAPIParser(strict_validation=False)

    def test_resolve_schema_ref(self, parser):
        """Test resolución de $ref a schema."""
        spec_content = """
openapi: "3.0.3"
info:
  title: Test
  version: "1.0"
paths:
  /users:
    get:
      responses:
        "200":
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/User"
components:
  schemas:
    User:
      type: object
      properties:
        id:
          type: string
"""
        spec = parser.parse_from_string(spec_content)

        response_schema = spec.paths["/users"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]
        assert response_schema["type"] == "object"
        assert "id" in response_schema["properties"]

    def test_resolve_nested_refs(self, parser):
        """Test resolución de refs anidadas."""
        spec_content = """
openapi: "3.0.3"
info:
  title: Test
  version: "1.0"
paths: {}
components:
  schemas:
    User:
      type: object
      properties:
        address:
          $ref: "#/components/schemas/Address"
    Address:
      type: object
      properties:
        street:
          type: string
"""
        spec = parser.parse_from_string(spec_content)

        user_schema = spec.components_schemas["User"]
        address = user_schema["properties"]["address"]
        assert address["type"] == "object"
        assert "street" in address["properties"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
