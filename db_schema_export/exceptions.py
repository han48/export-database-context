"""Custom exceptions for Database Schema Export Tool.

This module defines the exception hierarchy used throughout the tool.
All exceptions follow a unified error message format:

    [ERROR] {ErrorType}: {Description}
      → {Details}
      → {Hint}

Exception hierarchy:
    SchemaExportError (base)
    ├── EnvFileNotFoundError
    ├── MissingVariableError
    ├── NoDatabaseError
    ├── DatabaseConnectionError
    ├── FKMappingFileError
    │   ├── FKMapFileNotFoundError
    │   └── FKMapParseError
    ├── AllSchemasInvalidError
    ├── MetadataQueryError
    └── OutputWriteError

    SchemaNotFoundWarning (Warning subclass)
"""

from __future__ import annotations


class SchemaExportError(Exception):
    """Base exception for all Schema Export Tool errors.

    Provides a unified error message format for consistent CLI output.
    Subclasses should override `format_message()` to produce structured output.
    """

    def format_message(self) -> str:
        """Format the error message in the unified format.

        Returns:
            Formatted error string with [ERROR] prefix, details, and hints.
        """
        return f"[ERROR] {self.__class__.__name__}: {self.args[0] if self.args else 'Unknown error'}"

    def __str__(self) -> str:
        return self.format_message()


class EnvFileNotFoundError(SchemaExportError):
    """Raised when the .env file does not exist at the specified path.

    Attributes:
        path: The file path that was searched.
    """

    def __init__(self, path: str) -> None:
        self.path = path
        super().__init__(f"Cannot find .env file")

    def format_message(self) -> str:
        lines = [
            f"[ERROR] EnvFileNotFoundError: Cannot find .env file",
            f"  → Searched path: {self.path}",
            f"  → Hint: Use --env flag to specify a custom path",
        ]
        return "\n".join(lines)


class MissingVariableError(SchemaExportError):
    """Raised when required environment variables are missing from the .env file.

    Attributes:
        missing_vars: List of variable names that are missing.
    """

    def __init__(self, missing_vars: list[str]) -> None:
        self.missing_vars = missing_vars
        super().__init__("Required environment variables are missing")

    def format_message(self) -> str:
        missing_str = ", ".join(self.missing_vars)
        lines = [
            f"[ERROR] MissingVariableError: Required environment variables are missing",
            f"  → Missing: {missing_str}",
            f"  → Ensure these variables are defined in your .env file",
        ]
        return "\n".join(lines)


class NoDatabaseError(SchemaExportError):
    """Raised when neither DB_DATABASES nor DB_DATABASE is defined."""

    def __init__(self) -> None:
        super().__init__("No database specified")

    def format_message(self) -> str:
        lines = [
            f"[ERROR] NoDatabaseError: No database specified",
            f"  → Neither DB_DATABASES nor DB_DATABASE is defined in the .env file",
            f"  → Define at least one: DB_DATABASE=mydb or DB_DATABASES=db1,db2",
        ]
        return "\n".join(lines)


class DatabaseConnectionError(SchemaExportError):
    """Raised when a database connection fails.

    Displays host, port, and database name but never the password.

    Attributes:
        host: Database server hostname or IP.
        port: Database server port number.
        database: Name of the database that failed to connect.
        reason: Optional underlying error message.
    """

    def __init__(
        self, host: str, port: int, database: str, reason: str | None = None
    ) -> None:
        self.host = host
        self.port = port
        self.database = database
        self.reason = reason
        super().__init__(f"Cannot connect to database")

    def format_message(self) -> str:
        lines = [
            f"[ERROR] DatabaseConnectionError: Cannot connect to database",
            f"  → Host: {self.host}:{self.port}/{self.database}",
        ]
        if self.reason:
            lines.append(f"  → Reason: {self.reason}")
        lines.append(
            f"  → Check that the database server is running and credentials are correct"
        )
        return "\n".join(lines)


class FKMappingFileError(SchemaExportError):
    """Base exception for FK mapping file errors.

    Attributes:
        path: Path to the FK mapping file.
    """

    def __init__(self, path: str, message: str = "FK mapping file error") -> None:
        self.path = path
        super().__init__(message)


class FKMapFileNotFoundError(FKMappingFileError):
    """Raised when the FK mapping file does not exist.

    Attributes:
        path: The file path that was searched.
    """

    def __init__(self, path: str) -> None:
        self.path = path
        super().__init__(path, "FK mapping file not found")

    def format_message(self) -> str:
        lines = [
            f"[ERROR] FKMapFileNotFoundError: FK mapping file not found",
            f"  → Searched path: {self.path}",
            f"  → Hint: Check the --fk-map path or remove the flag to skip FK mapping",
        ]
        return "\n".join(lines)


class FKMapParseError(FKMappingFileError):
    """Raised when the FK mapping file contains invalid JSON.

    Attributes:
        path: Path to the FK mapping file.
        line_number: Line number where the parse error occurred, or None.
        parse_error: Description of the parsing error.
    """

    def __init__(
        self, path: str, parse_error: str, line_number: int | None = None
    ) -> None:
        self.path = path
        self.parse_error = parse_error
        self.line_number = line_number
        super().__init__(path, "FK mapping file contains invalid JSON")

    def format_message(self) -> str:
        lines = [
            f"[ERROR] FKMapParseError: FK mapping file contains invalid JSON",
            f"  → File: {self.path}",
        ]
        if self.line_number is not None:
            lines.append(f"  → Error at line {self.line_number}: {self.parse_error}")
        else:
            lines.append(f"  → Error: {self.parse_error}")
        lines.append(
            f"  → Ensure the file contains valid JSON with the correct structure"
        )
        return "\n".join(lines)


class AllSchemasInvalidError(SchemaExportError):
    """Raised when all specified schemas do not exist in the database.

    Attributes:
        schemas: List of schema names that were not found.
        database: Name of the database that was queried.
    """

    def __init__(self, schemas: list[str], database: str) -> None:
        self.schemas = schemas
        self.database = database
        super().__init__("All specified schemas are invalid")

    def format_message(self) -> str:
        schemas_str = ", ".join(self.schemas)
        lines = [
            f"[ERROR] AllSchemasInvalidError: All specified schemas are invalid",
            f"  → Schemas not found in database \"{self.database}\": {schemas_str}",
            f"  → Verify schema names with: SELECT schema_name FROM information_schema.schemata",
        ]
        return "\n".join(lines)


class MetadataQueryError(SchemaExportError):
    """Raised when a metadata query fails.

    Attributes:
        query_type: Type of metadata being queried (e.g., 'tables', 'columns').
        reason: Underlying error message.
        schema: Optional schema name where the error occurred.
    """

    def __init__(
        self, query_type: str, reason: str, schema: str | None = None
    ) -> None:
        self.query_type = query_type
        self.reason = reason
        self.schema = schema
        super().__init__(f"Failed to query {query_type} metadata")

    def format_message(self) -> str:
        lines = [
            f"[ERROR] MetadataQueryError: Failed to query {self.query_type} metadata",
        ]
        if self.schema:
            lines.append(f"  → Schema: {self.schema}")
        lines.append(f"  → Reason: {self.reason}")
        lines.append(
            f"  → Check database permissions or try excluding this metadata type"
        )
        return "\n".join(lines)


class OutputWriteError(SchemaExportError):
    """Raised when the output file cannot be written.

    Attributes:
        path: Path where the file was being written.
        reason: Underlying error message.
    """

    def __init__(self, path: str, reason: str) -> None:
        self.path = path
        self.reason = reason
        super().__init__(f"Cannot write output file")

    def format_message(self) -> str:
        lines = [
            f"[ERROR] OutputWriteError: Cannot write output file",
            f"  → Path: {self.path}",
            f"  → Reason: {self.reason}",
            f"  → Check directory permissions and available disk space",
        ]
        return "\n".join(lines)


class SchemaNotFoundWarning(UserWarning):
    """Warning issued when a specified schema does not exist in the database.

    This is a warning (not an error) because the tool continues processing
    with the remaining valid schemas.

    Attributes:
        schema: Schema name that was not found.
        database: Database name that was queried.
        remaining_schemas: List of valid schemas that will be processed.
    """

    def __init__(
        self, schema: str, database: str, remaining_schemas: list[str] | None = None
    ) -> None:
        self.schema = schema
        self.database = database
        self.remaining_schemas = remaining_schemas or []
        super().__init__(self.format_message())

    def format_message(self) -> str:
        lines = [
            f"[WARNING] SchemaNotFoundWarning: Schema does not exist",
            f"  → Schema \"{self.schema}\" not found in database \"{self.database}\"",
        ]
        if self.remaining_schemas:
            remaining_str = ", ".join(self.remaining_schemas)
            lines.append(f"  → Continuing with remaining schemas: {remaining_str}")
        return "\n".join(lines)

    def __str__(self) -> str:
        return self.format_message()
