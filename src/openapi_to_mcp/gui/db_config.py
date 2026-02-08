"""
Multi-Database Configuration for Enterprise Deployments.

Supports multiple database backends:
- SQLite (default, for development and small deployments)
- PostgreSQL (recommended for production)
- MongoDB (for document-oriented storage)

Configuration via environment variables:
- DATABASE_TYPE: sqlite, postgresql, or mongodb
- DATABASE_URL: Full connection URL (overrides individual settings)
- DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD: Individual settings
"""

import logging
import os
from enum import Enum
from typing import Any
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)


class DatabaseType(Enum):
    """Supported database types."""
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"
    MONGODB = "mongodb"


class DatabaseConfig:
    """Database configuration manager."""

    def __init__(self):
        self.db_type = self._get_db_type()
        self.connection_url = self._build_connection_url()

    def _get_db_type(self) -> DatabaseType:
        """Get database type from environment."""
        db_type_str = os.environ.get("DATABASE_TYPE", "sqlite").lower()
        try:
            return DatabaseType(db_type_str)
        except ValueError:
            logger.warning(f"Unknown DATABASE_TYPE '{db_type_str}', defaulting to SQLite")
            return DatabaseType.SQLITE

    def _build_connection_url(self) -> str:
        """Build database connection URL from environment variables."""
        # Check for explicit DATABASE_URL first
        if os.environ.get("DATABASE_URL"):
            url = os.environ["DATABASE_URL"]
            # Handle Heroku-style postgres:// URLs
            if url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql://", 1)
            return url

        # Build URL from individual components
        if self.db_type == DatabaseType.SQLITE:
            db_path = os.environ.get("DB_PATH", "openapi_mcp.db")
            return f"sqlite:///{db_path}"

        elif self.db_type == DatabaseType.POSTGRESQL:
            host = os.environ.get("DB_HOST", "localhost")
            port = os.environ.get("DB_PORT", "5432")
            name = os.environ.get("DB_NAME", "openapi_mcp")
            user = os.environ.get("DB_USER", "postgres")
            password = os.environ.get("DB_PASSWORD", "")

            if password:
                password = quote_plus(password)
                return f"postgresql://{user}:{password}@{host}:{port}/{name}"
            return f"postgresql://{user}@{host}:{port}/{name}"

        elif self.db_type == DatabaseType.MONGODB:
            host = os.environ.get("DB_HOST", "localhost")
            port = os.environ.get("DB_PORT", "27017")
            name = os.environ.get("DB_NAME", "openapi_mcp")
            user = os.environ.get("DB_USER", "")
            password = os.environ.get("DB_PASSWORD", "")

            if user and password:
                password = quote_plus(password)
                user = quote_plus(user)
                return f"mongodb://{user}:{password}@{host}:{port}/{name}"
            return f"mongodb://{host}:{port}/{name}"

        return "sqlite:///openapi_mcp.db"

    def get_sqlalchemy_url(self) -> str:
        """Get SQLAlchemy-compatible connection URL."""
        if self.db_type == DatabaseType.MONGODB:
            raise ValueError("MongoDB is not compatible with SQLAlchemy. Use get_mongodb_config().")
        return self.connection_url

    def get_mongodb_config(self) -> dict:
        """Get MongoDB connection configuration."""
        if self.db_type != DatabaseType.MONGODB:
            raise ValueError("Not configured for MongoDB.")

        return {
            "url": self.connection_url,
            "database": os.environ.get("DB_NAME", "openapi_mcp"),
        }

    def is_postgresql(self) -> bool:
        """Check if using PostgreSQL."""
        return self.db_type == DatabaseType.POSTGRESQL

    def is_mongodb(self) -> bool:
        """Check if using MongoDB."""
        return self.db_type == DatabaseType.MONGODB

    def is_sqlite(self) -> bool:
        """Check if using SQLite."""
        return self.db_type == DatabaseType.SQLITE

    def get_pool_config(self) -> dict:
        """Get connection pool configuration for SQLAlchemy."""
        if self.db_type == DatabaseType.SQLITE:
            return {}

        return {
            "pool_size": int(os.environ.get("DB_POOL_SIZE", "5")),
            "max_overflow": int(os.environ.get("DB_MAX_OVERFLOW", "10")),
            "pool_timeout": int(os.environ.get("DB_POOL_TIMEOUT", "30")),
            "pool_recycle": int(os.environ.get("DB_POOL_RECYCLE", "1800")),
            "pool_pre_ping": True,
        }


# Global configuration instance
_db_config: DatabaseConfig | None = None


def get_db_config() -> DatabaseConfig:
    """Get the global database configuration."""
    global _db_config
    if _db_config is None:
        _db_config = DatabaseConfig()
    return _db_config


def reset_db_config():
    """Reset the global database configuration (for testing)."""
    global _db_config
    _db_config = None


def configure_flask_app(app, output_dir: str | None = None):
    """
    Configure Flask app with the appropriate database settings.

    Args:
        app: Flask application instance
        output_dir: Output directory for SQLite database (if using SQLite)
    """
    from pathlib import Path

    config = get_db_config()

    if config.is_mongodb():
        # MongoDB doesn't use SQLAlchemy, configure separately
        logger.info("Configuring MongoDB connection")
        app.config["MONGODB_SETTINGS"] = config.get_mongodb_config()
        _init_mongodb(app)
    else:
        # SQLite or PostgreSQL use SQLAlchemy
        if config.is_sqlite() and output_dir:
            # For SQLite, use the output directory
            db_path = Path(output_dir).resolve() / "openapi_mcp.db"
            db_uri = f"sqlite:///{db_path.as_posix()}"
        else:
            db_uri = config.get_sqlalchemy_url()

        app.config["SQLALCHEMY_DATABASE_URI"] = db_uri
        app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

        # Apply pool configuration for PostgreSQL
        if config.is_postgresql():
            pool_config = config.get_pool_config()
            app.config["SQLALCHEMY_ENGINE_OPTIONS"] = pool_config
            logger.info(f"Configured PostgreSQL with pool_size={pool_config.get('pool_size')}")

        logger.info(f"Database configured: {config.db_type.value}")


def _init_mongodb(app):
    """Initialize MongoDB connection for Flask app."""
    try:
        from pymongo import MongoClient

        config = get_db_config().get_mongodb_config()
        client = MongoClient(config["url"])
        app.mongo_client = client
        app.mongo_db = client[config["database"]]

        # Test connection
        client.admin.command("ping")
        logger.info("MongoDB connection established")

    except ImportError:
        logger.error("pymongo not installed. Install with: pip install pymongo")
        raise
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        raise


# ========== MongoDB Adapters ==========

class MongoDBAdapter:
    """
    Adapter to provide SQLAlchemy-like interface for MongoDB.

    This allows using MongoDB with minimal code changes when the
    application is configured for MongoDB storage.
    """

    def __init__(self, app):
        self.app = app
        self.db = app.mongo_db

    def get_collection(self, name: str):
        """Get a MongoDB collection."""
        return self.db[name]

    # User operations
    def create_user(self, data: dict) -> dict:
        """Create a new user."""
        collection = self.get_collection("users")
        result = collection.insert_one(data)
        data["_id"] = result.inserted_id
        return data

    def get_user_by_id(self, user_id: int) -> dict | None:
        """Get user by ID."""
        return self.get_collection("users").find_one({"id": user_id})

    def get_user_by_username(self, username: str) -> dict | None:
        """Get user by username."""
        return self.get_collection("users").find_one({"username": username})

    def get_user_by_email(self, email: str) -> dict | None:
        """Get user by email."""
        return self.get_collection("users").find_one({"email": email})

    # Workspace operations
    def create_workspace(self, data: dict) -> dict:
        """Create a new workspace."""
        collection = self.get_collection("workspaces")
        result = collection.insert_one(data)
        data["_id"] = result.inserted_id
        return data

    def get_workspace(self, workspace_id: int) -> dict | None:
        """Get workspace by ID."""
        return self.get_collection("workspaces").find_one({"id": workspace_id})

    def list_workspaces(self, user_id: int) -> list[dict]:
        """List workspaces for a user."""
        members = self.get_collection("workspace_members").find({"user_id": user_id})
        workspace_ids = [m["workspace_id"] for m in members]
        return list(self.get_collection("workspaces").find({"id": {"$in": workspace_ids}}))

    # Activity log operations
    def log_activity(self, data: dict) -> dict:
        """Log an activity."""
        collection = self.get_collection("activity_logs")
        result = collection.insert_one(data)
        data["_id"] = result.inserted_id
        return data

    def get_activities(self, workspace_id: int = None, limit: int = 100) -> list[dict]:
        """Get activity logs."""
        query = {}
        if workspace_id:
            query["workspace_id"] = workspace_id
        return list(
            self.get_collection("activity_logs")
            .find(query)
            .sort("created_at", -1)
            .limit(limit)
        )

    # Audit log operations
    def create_audit_log(self, data: dict) -> dict:
        """Create an audit log entry."""
        collection = self.get_collection("audit_logs")
        result = collection.insert_one(data)
        data["_id"] = result.inserted_id
        return data

    def query_audit_logs(self, filters: dict, limit: int = 100) -> list[dict]:
        """Query audit logs with filters."""
        return list(
            self.get_collection("audit_logs")
            .find(filters)
            .sort("timestamp", -1)
            .limit(limit)
        )

    # Alert operations
    def create_alert(self, data: dict) -> dict:
        """Create an alert."""
        collection = self.get_collection("alerts")
        result = collection.insert_one(data)
        data["_id"] = result.inserted_id
        return data

    def get_alerts(self, status: str = None, limit: int = 100) -> list[dict]:
        """Get alerts."""
        query = {}
        if status:
            query["status"] = status
        return list(
            self.get_collection("alerts")
            .find(query)
            .sort("created_at", -1)
            .limit(limit)
        )

    # Report operations
    def create_report(self, data: dict) -> dict:
        """Create a generated report."""
        collection = self.get_collection("reports")
        result = collection.insert_one(data)
        data["_id"] = result.inserted_id
        return data

    def get_reports(self, report_type: str = None, limit: int = 50) -> list[dict]:
        """Get generated reports."""
        query = {}
        if report_type:
            query["report_type"] = report_type
        return list(
            self.get_collection("reports")
            .find(query)
            .sort("generated_at", -1)
            .limit(limit)
        )


def get_mongodb_adapter(app) -> MongoDBAdapter | None:
    """Get MongoDB adapter if configured for MongoDB."""
    config = get_db_config()
    if config.is_mongodb() and hasattr(app, "mongo_db"):
        return MongoDBAdapter(app)
    return None


# ========== PostgreSQL-specific utilities ==========

def get_postgresql_info() -> dict | None:
    """Get PostgreSQL server information."""
    config = get_db_config()
    if not config.is_postgresql():
        return None

    try:
        from sqlalchemy import create_engine, text

        engine = create_engine(config.connection_url)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.scalar()

            result = conn.execute(text("""
                SELECT pg_database.datname,
                       pg_size_pretty(pg_database_size(pg_database.datname)) as size
                FROM pg_database
                WHERE datname = current_database()
            """))
            row = result.fetchone()

        return {
            "version": version,
            "database": row[0] if row else None,
            "size": row[1] if row else None,
        }
    except Exception as e:
        logger.error(f"Failed to get PostgreSQL info: {e}")
        return None


def run_postgresql_migrations():
    """
    Run database migrations for PostgreSQL.

    This uses Alembic-style migrations if available,
    otherwise falls back to SQLAlchemy create_all.
    """
    config = get_db_config()
    if not config.is_postgresql():
        logger.warning("Migrations only supported for PostgreSQL")
        return

    try:
        from alembic.config import Config
        from alembic import command

        alembic_cfg = Config("alembic.ini")
        command.upgrade(alembic_cfg, "head")
        logger.info("PostgreSQL migrations completed")
    except ImportError:
        logger.info("Alembic not installed, using SQLAlchemy create_all")
    except FileNotFoundError:
        logger.info("No alembic.ini found, using SQLAlchemy create_all")


# ========== Health checks ==========

def check_database_health() -> dict:
    """
    Check database health and connectivity.

    Returns:
        Dict with health status and details
    """
    config = get_db_config()

    result = {
        "type": config.db_type.value,
        "healthy": False,
        "message": "",
        "details": {},
    }

    try:
        if config.is_mongodb():
            from pymongo import MongoClient

            mongo_config = config.get_mongodb_config()
            client = MongoClient(mongo_config["url"], serverSelectionTimeoutMS=5000)
            client.admin.command("ping")
            result["healthy"] = True
            result["message"] = "MongoDB connection successful"
            result["details"] = {
                "database": mongo_config["database"],
            }

        elif config.is_postgresql():
            from sqlalchemy import create_engine, text

            engine = create_engine(config.connection_url)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            result["healthy"] = True
            result["message"] = "PostgreSQL connection successful"

            # Get additional info
            pg_info = get_postgresql_info()
            if pg_info:
                result["details"] = pg_info

        else:  # SQLite
            import sqlite3
            from pathlib import Path

            # Extract path from URL
            db_path = config.connection_url.replace("sqlite:///", "")
            if Path(db_path).exists():
                conn = sqlite3.connect(db_path)
                conn.execute("SELECT 1")
                conn.close()
                result["healthy"] = True
                result["message"] = "SQLite database accessible"
                result["details"] = {
                    "path": db_path,
                    "size_mb": round(Path(db_path).stat().st_size / (1024 * 1024), 2),
                }
            else:
                result["healthy"] = True
                result["message"] = "SQLite database will be created on first use"
                result["details"] = {"path": db_path}

    except Exception as e:
        result["message"] = f"Database health check failed: {str(e)}"
        logger.error(result["message"])

    return result


# ========== Environment documentation ==========

def get_env_documentation() -> str:
    """Get documentation for database environment variables."""
    return """
Database Configuration Environment Variables
=============================================

General:
  DATABASE_TYPE      Database type: sqlite, postgresql, or mongodb (default: sqlite)
  DATABASE_URL       Full connection URL (overrides individual settings)

Individual Settings:
  DB_HOST           Database host (default: localhost)
  DB_PORT           Database port (default: 5432 for PostgreSQL, 27017 for MongoDB)
  DB_NAME           Database name (default: openapi_mcp)
  DB_USER           Database user
  DB_PASSWORD       Database password
  DB_PATH           SQLite database file path (default: openapi_mcp.db)

Connection Pool (PostgreSQL only):
  DB_POOL_SIZE      Connection pool size (default: 5)
  DB_MAX_OVERFLOW   Max overflow connections (default: 10)
  DB_POOL_TIMEOUT   Pool timeout in seconds (default: 30)
  DB_POOL_RECYCLE   Connection recycle time in seconds (default: 1800)

Examples:
  # SQLite (default)
  DATABASE_TYPE=sqlite
  DB_PATH=/data/openapi_mcp.db

  # PostgreSQL
  DATABASE_TYPE=postgresql
  DB_HOST=localhost
  DB_PORT=5432
  DB_NAME=openapi_mcp
  DB_USER=postgres
  DB_PASSWORD=secret

  # PostgreSQL with URL
  DATABASE_URL=postgresql://user:password@host:5432/dbname

  # MongoDB
  DATABASE_TYPE=mongodb
  DB_HOST=localhost
  DB_PORT=27017
  DB_NAME=openapi_mcp

  # MongoDB with authentication
  DATABASE_URL=mongodb://user:password@host:27017/openapi_mcp
"""
