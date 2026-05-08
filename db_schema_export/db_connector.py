"""Database connector module for Database Schema Export Tool.

This module provides an abstract interface for database connections and
concrete implementations for supported database systems.

Currently supported:
- PostgreSQL (via psycopg2)

Future support:
- MySQL (via mysql-connector-python)
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from db_schema_export.exceptions import DatabaseConnectionError
from db_schema_export.models import DbConfig


class DatabaseConnector(ABC):
    """Abstract interface for database connections.

    Provides a common interface for database operations regardless of the
    underlying database type. Supports context manager protocol for safe
    resource management.

    Usage:
        with create_connector(config, "mydb") as conn:
            results = conn.execute_query("SELECT * FROM users")
    """

    @abstractmethod
    def connect(self) -> None:
        """Establish a connection to the database.

        May be called multiple times safely - subsequent calls on an
        already-connected instance should be a no-op.

        Raises:
            DatabaseConnectionError: If the connection cannot be established.
        """
        ...

    @abstractmethod
    def close(self) -> None:
        """Close the database connection.

        Safe to call even if not connected or already closed.
        """
        ...

    @abstractmethod
    def execute_query(self, query: str, params: tuple = ()) -> list[dict]:
        """Execute a SQL query and return results as a list of dictionaries.

        Args:
            query: SQL query string. May contain %s placeholders for params.
            params: Tuple of parameters to substitute into the query.

        Returns:
            List of dictionaries where each dict represents a row,
            with column names as keys.

        Raises:
            DatabaseConnectionError: If not connected to the database.
        """
        ...

    def __enter__(self) -> DatabaseConnector:
        """Enter context manager - establishes connection."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context manager - closes connection."""
        self.close()


class PostgresConnector(DatabaseConnector):
    """PostgreSQL implementation using psycopg2.

    Uses RealDictCursor to return query results as dictionaries.

    Attributes:
        host: Database server hostname or IP address.
        port: Database server port number.
        database: Name of the database to connect to.
        username: Database username for authentication.
        password: Database password for authentication.
    """

    def __init__(
        self,
        host: str,
        port: int,
        database: str,
        username: str,
        password: str,
    ) -> None:
        self.host = host
        self.port = port
        self.database = database
        self.username = username
        self.password = password
        self._connection = None

    def connect(self) -> None:
        """Establish a connection to the PostgreSQL database.

        If already connected, this method is a no-op.

        Raises:
            DatabaseConnectionError: If the connection cannot be established.
                The error message includes host, port, and database name
                but never the password.
        """
        if self._connection is not None:
            return

        try:
            import psycopg2

            self._connection = psycopg2.connect(
                host=self.host,
                port=self.port,
                dbname=self.database,
                user=self.username,
                password=self.password,
            )
        except Exception as e:
            raise DatabaseConnectionError(
                host=self.host,
                port=self.port,
                database=self.database,
                reason=str(e),
            ) from e

    def close(self) -> None:
        """Close the PostgreSQL connection.

        Safe to call even if not connected or already closed.
        """
        if self._connection is not None:
            try:
                self._connection.close()
            except Exception:
                pass
            finally:
                self._connection = None

    def execute_query(self, query: str, params: tuple = ()) -> list[dict]:
        """Execute a SQL query and return results as a list of dictionaries.

        Uses psycopg2's RealDictCursor to return rows as dictionaries.

        Args:
            query: SQL query string with %s placeholders for params.
            params: Tuple of parameters to substitute into the query.

        Returns:
            List of dictionaries where each dict represents a row.

        Raises:
            DatabaseConnectionError: If not connected to the database.
        """
        if self._connection is None:
            raise DatabaseConnectionError(
                host=self.host,
                port=self.port,
                database=self.database,
                reason="Not connected. Call connect() first.",
            )

        import psycopg2.extras

        with self._connection.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        ) as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]


def create_connector(config: DbConfig, database: str) -> DatabaseConnector:
    """Factory function to create the appropriate database connector.

    Creates a connector instance based on the DB_CONNECTION type specified
    in the configuration.

    Args:
        config: Database configuration parsed from .env file.
        database: Name of the specific database to connect to.

    Returns:
        A DatabaseConnector instance configured for the specified database.

    Raises:
        NotImplementedError: If the DB_CONNECTION type is not supported
            (e.g., "mysql").
        ValueError: If the DB_CONNECTION type is unknown.
    """
    connection_type = config.connection.lower()

    if connection_type == "pgsql":
        return PostgresConnector(
            host=config.host,
            port=config.port,
            database=database,
            username=config.username,
            password=config.password,
        )
    elif connection_type == "mysql":
        raise NotImplementedError(
            "MySQL support is not yet implemented. "
            "Currently only PostgreSQL (DB_CONNECTION=pgsql) is supported."
        )
    else:
        raise ValueError(
            f"Unsupported DB_CONNECTION type: '{config.connection}'. "
            f"Supported types: pgsql, mysql (future)."
        )
