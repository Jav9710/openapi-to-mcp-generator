"""
Integraciones con GitHub y GitLab.

Permite importar especificaciones OpenAPI directamente desde
repositorios de GitHub y GitLab usando sus APIs.
"""

import base64
import logging
from dataclasses import dataclass

import requests

logger = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"
GITLAB_API = "https://gitlab.com/api/v4"

# Extensiones comunes de archivos OpenAPI
OPENAPI_EXTENSIONS = (".yaml", ".yml", ".json")
OPENAPI_PATTERNS = ("openapi", "swagger", "api-spec", "api_spec")


@dataclass
class RepoFile:
    """Archivo encontrado en un repositorio."""
    path: str
    name: str
    size: int
    download_url: str | None = None

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "name": self.name,
            "size": self.size,
            "download_url": self.download_url,
        }


@dataclass
class RepoInfo:
    """Informacion basica de un repositorio."""
    name: str
    full_name: str
    description: str | None
    default_branch: str
    url: str
    private: bool

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "full_name": self.full_name,
            "description": self.description,
            "default_branch": self.default_branch,
            "url": self.url,
            "private": self.private,
        }


class GitHubIntegration:
    """Integracion con GitHub API."""

    def __init__(self, token: str):
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "OpenAPI-to-MCP-Generator/1.0",
        }

    def list_repos(self, per_page: int = 30, page: int = 1) -> list[RepoInfo]:
        """Lista repositorios del usuario autenticado."""
        resp = requests.get(
            f"{GITHUB_API}/user/repos",
            headers=self.headers,
            params={"per_page": per_page, "page": page, "sort": "updated"},
            timeout=15,
        )
        resp.raise_for_status()

        return [
            RepoInfo(
                name=r["name"],
                full_name=r["full_name"],
                description=r.get("description"),
                default_branch=r.get("default_branch", "main"),
                url=r["html_url"],
                private=r["private"],
            )
            for r in resp.json()
        ]

    def list_branches(self, repo_full_name: str) -> list[str]:
        """Lista las branches de un repositorio."""
        resp = requests.get(
            f"{GITHUB_API}/repos/{repo_full_name}/branches",
            headers=self.headers,
            params={"per_page": 100},
            timeout=15,
        )
        resp.raise_for_status()
        return [b["name"] for b in resp.json()]

    def find_openapi_files(self, repo_full_name: str, branch: str = None) -> list[RepoFile]:
        """Busca archivos OpenAPI en un repositorio."""
        params = {}
        if branch:
            params["ref"] = branch

        # Buscar en la raiz y directorios comunes
        files = []
        search_paths = ["", "api", "docs", "spec", "specs", "openapi", "swagger"]

        for search_path in search_paths:
            try:
                url = f"{GITHUB_API}/repos/{repo_full_name}/contents/{search_path}"
                resp = requests.get(url, headers=self.headers, params=params, timeout=15)
                if resp.status_code != 200:
                    continue

                for item in resp.json():
                    if item["type"] == "file" and self._is_openapi_candidate(item["name"]):
                        files.append(RepoFile(
                            path=item["path"],
                            name=item["name"],
                            size=item.get("size", 0),
                            download_url=item.get("download_url"),
                        ))
            except Exception as e:
                logger.debug(f"Error searching {search_path}: {e}")

        return files

    def fetch_file_content(self, repo_full_name: str, file_path: str, branch: str = None) -> str:
        """Descarga el contenido de un archivo."""
        params = {}
        if branch:
            params["ref"] = branch

        resp = requests.get(
            f"{GITHUB_API}/repos/{repo_full_name}/contents/{file_path}",
            headers=self.headers,
            params=params,
            timeout=30,
        )
        resp.raise_for_status()

        data = resp.json()
        if data.get("encoding") == "base64":
            return base64.b64decode(data["content"]).decode("utf-8")

        # Fallback: descargar via download_url
        if data.get("download_url"):
            dl_resp = requests.get(data["download_url"], headers=self.headers, timeout=30)
            dl_resp.raise_for_status()
            return dl_resp.text

        raise ValueError("No se pudo obtener el contenido del archivo")

    def _is_openapi_candidate(self, filename: str) -> bool:
        """Verifica si un archivo puede ser un spec OpenAPI."""
        lower = filename.lower()
        if not any(lower.endswith(ext) for ext in OPENAPI_EXTENSIONS):
            return False
        return any(p in lower for p in OPENAPI_PATTERNS) or lower in (
            "openapi.yaml", "openapi.yml", "openapi.json",
            "swagger.yaml", "swagger.yml", "swagger.json",
            "api.yaml", "api.yml", "api.json",
        )


class GitLabIntegration:
    """Integracion con GitLab API."""

    def __init__(self, token: str, base_url: str = GITLAB_API):
        self.token = token
        self.base_url = base_url.rstrip("/")
        self.headers = {
            "PRIVATE-TOKEN": token,
            "User-Agent": "OpenAPI-to-MCP-Generator/1.0",
        }

    def list_repos(self, per_page: int = 30, page: int = 1) -> list[RepoInfo]:
        """Lista proyectos del usuario autenticado."""
        resp = requests.get(
            f"{self.base_url}/projects",
            headers=self.headers,
            params={
                "membership": True,
                "per_page": per_page,
                "page": page,
                "order_by": "last_activity_at",
            },
            timeout=15,
        )
        resp.raise_for_status()

        return [
            RepoInfo(
                name=r["name"],
                full_name=r["path_with_namespace"],
                description=r.get("description"),
                default_branch=r.get("default_branch", "main"),
                url=r["web_url"],
                private=r.get("visibility") == "private",
            )
            for r in resp.json()
        ]

    def list_branches(self, project_id: int | str) -> list[str]:
        """Lista branches de un proyecto."""
        # URL-encode el project path si es string
        from urllib.parse import quote
        pid = quote(str(project_id), safe="")

        resp = requests.get(
            f"{self.base_url}/projects/{pid}/repository/branches",
            headers=self.headers,
            params={"per_page": 100},
            timeout=15,
        )
        resp.raise_for_status()
        return [b["name"] for b in resp.json()]

    def find_openapi_files(self, project_id: int | str, branch: str = None) -> list[RepoFile]:
        """Busca archivos OpenAPI en un proyecto."""
        from urllib.parse import quote
        pid = quote(str(project_id), safe="")

        params = {"recursive": True, "per_page": 100}
        if branch:
            params["ref"] = branch

        files = []
        try:
            resp = requests.get(
                f"{self.base_url}/projects/{pid}/repository/tree",
                headers=self.headers,
                params=params,
                timeout=15,
            )
            resp.raise_for_status()

            for item in resp.json():
                if item["type"] == "blob" and self._is_openapi_candidate(item["name"]):
                    files.append(RepoFile(
                        path=item["path"],
                        name=item["name"],
                        size=0,  # GitLab tree no incluye size
                    ))
        except Exception as e:
            logger.error(f"Error listing GitLab files: {e}")

        return files

    def fetch_file_content(self, project_id: int | str, file_path: str, branch: str = None) -> str:
        """Descarga el contenido de un archivo."""
        from urllib.parse import quote
        pid = quote(str(project_id), safe="")
        fpath = quote(file_path, safe="")

        params = {}
        if branch:
            params["ref"] = branch

        resp = requests.get(
            f"{self.base_url}/projects/{pid}/repository/files/{fpath}/raw",
            headers=self.headers,
            params=params,
            timeout=30,
        )
        resp.raise_for_status()
        return resp.text

    def _is_openapi_candidate(self, filename: str) -> bool:
        """Verifica si un archivo puede ser un spec OpenAPI."""
        lower = filename.lower()
        if not any(lower.endswith(ext) for ext in OPENAPI_EXTENSIONS):
            return False
        return any(p in lower for p in OPENAPI_PATTERNS) or lower in (
            "openapi.yaml", "openapi.yml", "openapi.json",
            "swagger.yaml", "swagger.yml", "swagger.json",
            "api.yaml", "api.yml", "api.json",
        )
