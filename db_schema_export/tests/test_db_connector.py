"""Unit tests for db_schema_export.db_connector module."""

import sys
from unittest.mock import MagicMock, patch

import pytest

from db_schema_export.db_connector import (
    DatabaseConnector,
    PostgresConnector,
    create_connector,
)
from db_schema_export.exceptions import DatabaseConnectionError
from db_schema_export.models import DbConfig


# --- Mock psycopg2 setup ---


@pytest.fixture(autouse=True)
def mock_psycopg2():
    """Mock psycopg2 module so tests work without it installed."""
    mock_module = MagicMock()
    mock_extras = MagicMock()
    mock_module.extras = mock_extras

    with patch.dict(sys.modules, {"psycopg2": mock_module, "psycopg2.extras": mock_extras}):
        yield mock_module, mock_extras


# --- Fixtures ---


@pytest.fixture
def sample_config():
    """Sample DbConfig for testing."""
    return DbConfig(
        connection="pgsql",
        host="127.0.0.1",
        port=5432,
        username="testuser",
        password="testpass",
        databases=["testdb"],
    )


@pytest.fixture
def postgres_connector():
    """Create a PostgresConnector instance for testing."""
    return PostgresConnector(
        host="127.0.0.1",
        port=5432,
        database="testdb",
        username="testuser",
        password="testpass",
    )


# --- DatabaseConnector Abstract Interface Tests ---


class TestDatabaseConnectorInterface:
    """Tests for the abstract DatabaseConnector interface."""

    def test_cannot_instantiate_abstract_class(self):
        """DatabaseConnector cannot be instantiated directly."""
        with pytest.raises(TypeError):
            DatabaseConnector()

    def test_subclass_must_implement_connect(self):
        """Subclass without connect() raises TypeError."""

        class IncompleteConnector(DatabaseConnector):
            def close(self):
                pass

            def execute_query(self, query, params=()):
                return []

        with pytest.raises(TypeError):
            IncompleteConnector()

    def test_subclass_must_implement_close(self):
        """Subclass without close() raises TypeError."""

        class IncompleteConnector(DatabaseConnector):
            def connect(self):
                pass

            def execute_query(self, query, params=()):
                return []

        with pytest.raises(TypeError):
            IncompleteConnector()

    def test_subclass_must_implement_execute_query(self):
        """Subclass without execute_query() raises TypeError."""

        class IncompleteConnector(DatabaseConnector):
            def connect(self):
                pass

            def close(self):
                pass

        with pytest.raises(TypeError):
            IncompleteConnector()


# --- PostgresConnector Tests ---


class TestPostgresConnector:
    """Tests for the PostgresConnector implementation."""

    def test_init_stores_connection_params(self, postgres_connector):
        """Constructor stores all connection parameters."""
        assert postgres_connector.host == "127.0.0.1"
        assert postgres_connector.port == 5432
        assert postgres_connector.database == "testdb"
        assert postgres_connector.username == "testuser"
        assert postgres_connector.password == "testpass"
        assert postgres_connector._connection is None

    def test_connect_calls_psycopg2(self, postgres_connector, mock_psycopg2):
        """connect() calls psycopg2.connect with correct parameters."""
        mock_module, _ = mock_psycopg2
        mock_conn = MagicMock()
        mock_module.connect.return_value = mock_conn

        postgres_connector.connect()

        mock_module.connect.assert_called_once_with(
            host="127.0.0.1",
            port=5432,
            dbname="testdb",
            user="testuser",
            password="testpass",
        )
        assert postgres_connector._connection is mock_conn

    def test_connect_multiple_times_is_noop(self, postgres_connector, mock_psycopg2):
        """Calling connect() when already connected does nothing."""
        mock_module, _ = mock_psycopg2
        mock_conn = MagicMock()
        mock_module.connect.return_value = mock_conn

        postgres_connector.connect()
        postgres_connector.connect()  # Second call should be no-op

        mock_module.connect.assert_called_once()

    def test_connect_failure_raises_database_connection_error(
        self, postgres_connector, mock_psycopg2
    ):
        """connect() raises DatabaseConnectionError on failure."""
        mock_module, _ = mock_psycopg2
        mock_module.connect.side_effect = Exception("Connection refused")

        with pytest.raises(DatabaseConnectionError) as exc_info:
            postgres_connector.connect()

        error = exc_info.value
        assert error.host == "127.0.0.1"
        assert error.port == 5432
        assert error.database == "testdb"
        assert "Connection refused" in error.reason

    def test_connect_error_does_not_expose_password(
        self, postgres_connector, mock_psycopg2
    ):
        """Connection error message does not contain the password."""
        mock_module, _ = mock_psycopg2
        mock_module.connect.side_effect = Exception("auth failed")

        with pytest.raises(DatabaseConnectionError) as exc_info:
            postgres_connector.connect()

        error_message = exc_info.value.format_message()
        assert "testpass" not in error_message

    def test_close_closes_connection(self, postgres_connector, mock_psycopg2):
        """close() closes the underlying connection."""
        mock_module, _ = mock_psycopg2
        mock_conn = MagicMock()
        mock_module.connect.return_value = mock_conn

        postgres_connector.connect()
        postgres_connector.close()

        mock_conn.close.assert_called_once()
        assert postgres_connector._connection is None

    def test_close_when_not_connected_is_safe(self, postgres_connector):
        """close() does not raise when not connected."""
        postgres_connector.close()  # Should not raise

    def test_close_handles_exception_gracefully(
        self, postgres_connector, mock_psycopg2
    ):
        """close() handles exceptions from underlying connection.close()."""
        mock_module, _ = mock_psycopg2
        mock_conn = MagicMock()
        mock_conn.close.side_effect = Exception("Already closed")
        mock_module.connect.return_value = mock_conn

        postgres_connector.connect()
        postgres_connector.close()  # Should not raise

        assert postgres_connector._connection is None

    def test_execute_query_returns_list_of_dicts(
        self, postgres_connector, mock_psycopg2
    ):
        """execute_query() returns results as list of dictionaries."""
        mock_module, mock_extras = mock_psycopg2
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {"id": 1, "name": "Alice"},
            {"id": 2, "name": "Bob"},
        ]
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_module.connect.return_value = mock_conn

        postgres_connector.connect()
        results = postgres_connector.execute_query("SELECT * FROM users")

        assert results == [
            {"id": 1, "name": "Alice"},
            {"id": 2, "name": "Bob"},
        ]

    def test_execute_query_with_params(self, postgres_connector, mock_psycopg2):
        """execute_query() passes params to cursor.execute()."""
        mock_module, mock_extras = mock_psycopg2
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [{"id": 1}]
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_module.connect.return_value = mock_conn

        postgres_connector.connect()
        postgres_connector.execute_query(
            "SELECT * FROM users WHERE id = %s", (1,)
        )

        mock_cursor.execute.assert_called_once_with(
            "SELECT * FROM users WHERE id = %s", (1,)
        )

    def test_execute_query_without_connection_raises_error(self, postgres_connector):
        """execute_query() raises DatabaseConnectionError when not connected."""
        with pytest.raises(DatabaseConnectionError) as exc_info:
            postgres_connector.execute_query("SELECT 1")

        assert "Not connected" in exc_info.value.reason

    def test_execute_query_uses_real_dict_cursor(
        self, postgres_connector, mock_psycopg2
    ):
        """execute_query() uses RealDictCursor for dict results."""
        mock_module, mock_extras = mock_psycopg2
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_module.connect.return_value = mock_conn

        postgres_connector.connect()
        postgres_connector.execute_query("SELECT 1")

        # Verify cursor was created with RealDictCursor
        mock_conn.cursor.assert_called_once_with(
            cursor_factory=mock_extras.RealDictCursor
        )


# --- Context Manager Tests ---


class TestContextManager:
    """Tests for the context manager protocol."""

    def test_context_manager_connects_on_enter(
        self, postgres_connector, mock_psycopg2
    ):
        """__enter__ calls connect()."""
        mock_module, _ = mock_psycopg2
        mock_conn = MagicMock()
        mock_module.connect.return_value = mock_conn

        with postgres_connector as conn:
            assert conn is postgres_connector
            assert postgres_connector._connection is mock_conn

    def test_context_manager_closes_on_exit(
        self, postgres_connector, mock_psycopg2
    ):
        """__exit__ calls close()."""
        mock_module, _ = mock_psycopg2
        mock_conn = MagicMock()
        mock_module.connect.return_value = mock_conn

        with postgres_connector:
            pass

        mock_conn.close.assert_called_once()
        assert postgres_connector._connection is None

    def test_context_manager_closes_on_exception(
        self, postgres_connector, mock_psycopg2
    ):
        """__exit__ closes connection even when exception occurs."""
        mock_module, _ = mock_psycopg2
        mock_conn = MagicMock()
        mock_module.connect.return_value = mock_conn

        with pytest.raises(ValueError):
            with postgres_connector:
                raise ValueError("test error")

        mock_conn.close.assert_called_once()
        assert postgres_connector._connection is None


# --- Factory Function Tests ---


class TestCreateConnector:
    """Tests for the create_connector factory function."""

    def test_pgsql_returns_postgres_connector(self, sample_config):
        """create_connector with 'pgsql' returns PostgresConnector."""
        connector = create_connector(sample_config, "testdb")

        assert isinstance(connector, PostgresConnector)
        assert connector.host == "127.0.0.1"
        assert connector.port == 5432
        assert connector.database == "testdb"
        assert connector.username == "testuser"
        assert connector.password == "testpass"

    def test_pgsql_case_insensitive(self, sample_config):
        """create_connector handles 'PGSQL' case-insensitively."""
        sample_config.connection = "PGSQL"
        connector = create_connector(sample_config, "testdb")

        assert isinstance(connector, PostgresConnector)

    def test_mysql_raises_not_implemented(self, sample_config):
        """create_connector with 'mysql' raises NotImplementedError."""
        sample_config.connection = "mysql"

        with pytest.raises(NotImplementedError) as exc_info:
            create_connector(sample_config, "testdb")

        assert "MySQL" in str(exc_info.value)
        assert "not yet implemented" in str(exc_info.value)

    def test_unknown_connection_type_raises_value_error(self, sample_config):
        """create_connector with unknown type raises ValueError."""
        sample_config.connection = "sqlite"

        with pytest.raises(ValueError) as exc_info:
            create_connector(sample_config, "testdb")

        assert "sqlite" in str(exc_info.value)
        assert "Unsupported" in str(exc_info.value)

    def test_uses_provided_database_name(self, sample_config):
        """create_connector uses the database parameter, not config.databases."""
        connector = create_connector(sample_config, "other_db")

        assert isinstance(connector, PostgresConnector)
        assert connector.database == "other_db"
