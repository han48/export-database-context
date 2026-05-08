"""Tests for custom exceptions module."""

import pytest

from db_schema_export.exceptions import (
    AllSchemasInvalidError,
    DatabaseConnectionError,
    EnvFileNotFoundError,
    FKMapFileNotFoundError,
    FKMappingFileError,
    FKMapParseError,
    MetadataQueryError,
    MissingVariableError,
    NoDatabaseError,
    OutputWriteError,
    SchemaExportError,
    SchemaNotFoundWarning,
)


class TestExceptionHierarchy:
    """Test that exception classes follow the correct inheritance hierarchy."""

    def test_base_exception_is_exception(self):
        assert issubclass(SchemaExportError, Exception)

    def test_env_file_not_found_inherits_base(self):
        assert issubclass(EnvFileNotFoundError, SchemaExportError)

    def test_missing_variable_inherits_base(self):
        assert issubclass(MissingVariableError, SchemaExportError)

    def test_no_database_inherits_base(self):
        assert issubclass(NoDatabaseError, SchemaExportError)

    def test_database_connection_inherits_base(self):
        assert issubclass(DatabaseConnectionError, SchemaExportError)

    def test_fk_mapping_file_inherits_base(self):
        assert issubclass(FKMappingFileError, SchemaExportError)

    def test_fk_map_file_not_found_inherits_fk_mapping(self):
        assert issubclass(FKMapFileNotFoundError, FKMappingFileError)

    def test_fk_map_parse_error_inherits_fk_mapping(self):
        assert issubclass(FKMapParseError, FKMappingFileError)

    def test_all_schemas_invalid_inherits_base(self):
        assert issubclass(AllSchemasInvalidError, SchemaExportError)

    def test_metadata_query_inherits_base(self):
        assert issubclass(MetadataQueryError, SchemaExportError)

    def test_output_write_inherits_base(self):
        assert issubclass(OutputWriteError, SchemaExportError)

    def test_schema_not_found_warning_is_warning(self):
        assert issubclass(SchemaNotFoundWarning, UserWarning)


class TestEnvFileNotFoundError:
    """Test EnvFileNotFoundError formatting and attributes."""

    def test_stores_path(self):
        err = EnvFileNotFoundError("/home/user/project/.env")
        assert err.path == "/home/user/project/.env"

    def test_format_message(self):
        err = EnvFileNotFoundError("/home/user/project/.env")
        msg = str(err)
        assert "[ERROR] EnvFileNotFoundError: Cannot find .env file" in msg
        assert "→ Searched path: /home/user/project/.env" in msg
        assert "→ Hint: Use --env flag to specify a custom path" in msg

    def test_is_catchable_as_base(self):
        with pytest.raises(SchemaExportError):
            raise EnvFileNotFoundError("/path/.env")


class TestMissingVariableError:
    """Test MissingVariableError formatting and attributes."""

    def test_stores_missing_vars(self):
        err = MissingVariableError(["DB_HOST", "DB_PASSWORD"])
        assert err.missing_vars == ["DB_HOST", "DB_PASSWORD"]

    def test_format_message_single_var(self):
        err = MissingVariableError(["DB_HOST"])
        msg = str(err)
        assert "[ERROR] MissingVariableError" in msg
        assert "→ Missing: DB_HOST" in msg

    def test_format_message_multiple_vars(self):
        err = MissingVariableError(["DB_HOST", "DB_PASSWORD"])
        msg = str(err)
        assert "→ Missing: DB_HOST, DB_PASSWORD" in msg
        assert "→ Ensure these variables are defined in your .env file" in msg


class TestNoDatabaseError:
    """Test NoDatabaseError formatting."""

    def test_format_message(self):
        err = NoDatabaseError()
        msg = str(err)
        assert "[ERROR] NoDatabaseError: No database specified" in msg
        assert "→ Neither DB_DATABASES nor DB_DATABASE" in msg
        assert "→ Define at least one" in msg


class TestDatabaseConnectionError:
    """Test DatabaseConnectionError formatting and attributes."""

    def test_stores_connection_info(self):
        err = DatabaseConnectionError("localhost", 5432, "mydb")
        assert err.host == "localhost"
        assert err.port == 5432
        assert err.database == "mydb"

    def test_format_message_without_reason(self):
        err = DatabaseConnectionError("localhost", 5432, "mydb")
        msg = str(err)
        assert "[ERROR] DatabaseConnectionError: Cannot connect to database" in msg
        assert "→ Host: localhost:5432/mydb" in msg
        assert "→ Check that the database server is running" in msg

    def test_format_message_with_reason(self):
        err = DatabaseConnectionError("db.host.com", 5433, "prod", "Connection refused")
        msg = str(err)
        assert "→ Host: db.host.com:5433/prod" in msg
        assert "→ Reason: Connection refused" in msg

    def test_no_password_in_message(self):
        err = DatabaseConnectionError("localhost", 5432, "mydb", "auth failed")
        msg = str(err)
        assert "password" not in msg.lower()


class TestFKMapFileNotFoundError:
    """Test FKMapFileNotFoundError formatting and attributes."""

    def test_stores_path(self):
        err = FKMapFileNotFoundError("/path/to/fk_map.json")
        assert err.path == "/path/to/fk_map.json"

    def test_format_message(self):
        err = FKMapFileNotFoundError("/path/to/fk_map.json")
        msg = str(err)
        assert "[ERROR] FKMapFileNotFoundError: FK mapping file not found" in msg
        assert "→ Searched path: /path/to/fk_map.json" in msg
        assert "→ Hint:" in msg

    def test_is_catchable_as_fk_mapping_file_error(self):
        with pytest.raises(FKMappingFileError):
            raise FKMapFileNotFoundError("/path/fk.json")


class TestFKMapParseError:
    """Test FKMapParseError formatting and attributes."""

    def test_stores_attributes(self):
        err = FKMapParseError("/path/fk.json", "Unexpected token", 15)
        assert err.path == "/path/fk.json"
        assert err.parse_error == "Unexpected token"
        assert err.line_number == 15

    def test_format_message_with_line_number(self):
        err = FKMapParseError("/path/fk.json", "Unexpected token", 15)
        msg = str(err)
        assert "[ERROR] FKMapParseError: FK mapping file contains invalid JSON" in msg
        assert "→ File: /path/fk.json" in msg
        assert "→ Error at line 15: Unexpected token" in msg

    def test_format_message_without_line_number(self):
        err = FKMapParseError("/path/fk.json", "Empty file")
        msg = str(err)
        assert "→ Error: Empty file" in msg
        assert "line" not in msg.split("→ Error:")[1]

    def test_is_catchable_as_fk_mapping_file_error(self):
        with pytest.raises(FKMappingFileError):
            raise FKMapParseError("/path/fk.json", "bad json")


class TestAllSchemasInvalidError:
    """Test AllSchemasInvalidError formatting and attributes."""

    def test_stores_attributes(self):
        err = AllSchemasInvalidError(["salesforce", "custom"], "mydb")
        assert err.schemas == ["salesforce", "custom"]
        assert err.database == "mydb"

    def test_format_message(self):
        err = AllSchemasInvalidError(["salesforce", "custom"], "mydb")
        msg = str(err)
        assert "[ERROR] AllSchemasInvalidError" in msg
        assert 'Schemas not found in database "mydb": salesforce, custom' in msg
        assert "→ Verify schema names" in msg


class TestMetadataQueryError:
    """Test MetadataQueryError formatting and attributes."""

    def test_stores_attributes(self):
        err = MetadataQueryError("tables", "permission denied", "public")
        assert err.query_type == "tables"
        assert err.reason == "permission denied"
        assert err.schema == "public"

    def test_format_message_with_schema(self):
        err = MetadataQueryError("tables", "permission denied", "public")
        msg = str(err)
        assert "[ERROR] MetadataQueryError: Failed to query tables metadata" in msg
        assert "→ Schema: public" in msg
        assert "→ Reason: permission denied" in msg

    def test_format_message_without_schema(self):
        err = MetadataQueryError("functions", "timeout")
        msg = str(err)
        assert "Failed to query functions metadata" in msg
        assert "Schema:" not in msg
        assert "→ Reason: timeout" in msg


class TestOutputWriteError:
    """Test OutputWriteError formatting and attributes."""

    def test_stores_attributes(self):
        err = OutputWriteError("/output/schema.md", "Permission denied")
        assert err.path == "/output/schema.md"
        assert err.reason == "Permission denied"

    def test_format_message(self):
        err = OutputWriteError("/output/schema.md", "Permission denied")
        msg = str(err)
        assert "[ERROR] OutputWriteError: Cannot write output file" in msg
        assert "→ Path: /output/schema.md" in msg
        assert "→ Reason: Permission denied" in msg
        assert "→ Check directory permissions" in msg


class TestSchemaNotFoundWarning:
    """Test SchemaNotFoundWarning formatting and attributes."""

    def test_stores_attributes(self):
        warn = SchemaNotFoundWarning("salesforce", "mydb", ["public"])
        assert warn.schema == "salesforce"
        assert warn.database == "mydb"
        assert warn.remaining_schemas == ["public"]

    def test_format_message_with_remaining(self):
        warn = SchemaNotFoundWarning("salesforce", "mydb", ["public"])
        msg = str(warn)
        assert "[WARNING] SchemaNotFoundWarning: Schema does not exist" in msg
        assert '→ Schema "salesforce" not found in database "mydb"' in msg
        assert "→ Continuing with remaining schemas: public" in msg

    def test_format_message_without_remaining(self):
        warn = SchemaNotFoundWarning("salesforce", "mydb")
        msg = str(warn)
        assert "[WARNING] SchemaNotFoundWarning" in msg
        assert "Continuing with remaining" not in msg

    def test_is_warning_subclass(self):
        warn = SchemaNotFoundWarning("test", "db")
        assert isinstance(warn, UserWarning)
