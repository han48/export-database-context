"""Data models for Database Schema Export Tool.

This module defines all dataclasses used throughout the tool for representing
database metadata including tables, columns, foreign keys, views, functions,
triggers, and configuration.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ColumnMetadata:
    """Represents metadata for a single database column.

    Attributes:
        name: Column name.
        data_type: SQL data type (e.g., 'integer', 'varchar', 'timestamp').
        is_nullable: Whether the column allows NULL values.
        default_value: Default value expression, or None if no default.
        is_primary_key: Whether this column is part of the primary key.
        is_foreign_key: Whether this column is part of a foreign key constraint.
        comment: Column comment from pg_catalog, or None.
        max_length: Maximum character length for varchar/char types, or None.
    """

    name: str
    data_type: str
    is_nullable: bool
    default_value: str | None
    is_primary_key: bool = False
    is_foreign_key: bool = False
    comment: str | None = None
    max_length: int | None = None


@dataclass
class TableMetadata:
    """Represents metadata for a database table.

    Attributes:
        schema: Schema name containing the table (e.g., 'public').
        name: Table name.
        columns: List of column metadata for this table.
        comment: Table comment from pg_catalog, or None.
    """

    schema: str
    name: str
    columns: list[ColumnMetadata] = field(default_factory=list)
    comment: str | None = None


@dataclass
class ForeignKeyMetadata:
    """Represents a foreign key relationship between two tables.

    Attributes:
        source_schema: Schema of the referencing table.
        source_table: Name of the referencing table.
        source_column: Column in the referencing table.
        target_schema: Schema of the referenced table.
        target_table: Name of the referenced table.
        target_column: Column in the referenced table.
        status: Either 'confirmed' (from DB constraints) or 'inferred' (from FK engine).
        confidence: Confidence level for inferred FKs ('high', 'medium', 'low'), None for confirmed.
    """

    source_schema: str
    source_table: str
    source_column: str
    target_schema: str
    target_table: str
    target_column: str
    status: str = "confirmed"
    confidence: str | None = None


@dataclass
class ViewMetadata:
    """Represents metadata for a database view.

    Attributes:
        schema: Schema name containing the view.
        name: View name.
        definition: SQL definition of the view.
        columns: List of column metadata for this view.
    """

    schema: str
    name: str
    definition: str
    columns: list[ColumnMetadata] = field(default_factory=list)


@dataclass
class FunctionMetadata:
    """Represents metadata for a database function or procedure.

    Attributes:
        schema: Schema name containing the function.
        name: Function name.
        arguments: Function arguments as a formatted string (e.g., 'price integer, rate numeric').
        return_type: Return type of the function.
        language: Programming language (e.g., 'plpgsql', 'sql').
        func_type: Type classification: 'function', 'procedure', or 'trigger function'.
    """

    schema: str
    name: str
    arguments: str
    return_type: str
    language: str
    func_type: str


@dataclass
class TriggerMetadata:
    """Represents metadata for a database trigger.

    Attributes:
        schema: Schema name containing the trigger.
        name: Trigger name.
        table_name: Name of the table the trigger is attached to.
        timing: When the trigger fires: 'BEFORE', 'AFTER', or 'INSTEAD OF'.
        event: Event that fires the trigger: 'INSERT', 'UPDATE', 'DELETE', or combined.
        function_name: Name of the function called by the trigger.
    """

    schema: str
    name: str
    table_name: str
    timing: str
    event: str
    function_name: str


@dataclass
class TypeMetadata:
    """Represents metadata for a custom database type.

    Attributes:
        schema: Schema name containing the type.
        name: Type name.
        type_type: Type category: 'composite', 'enum', 'domain', 'range', 'base'.
        definition: Type definition details (enum labels, composite columns, domain base type).
    """

    schema: str
    name: str
    type_type: str
    definition: str


@dataclass
class SequenceMetadata:
    """Represents metadata for a database sequence.

    Attributes:
        schema: Schema name containing the sequence.
        name: Sequence name.
        data_type: Data type of the sequence (e.g., 'bigint').
        start_value: Start value of the sequence.
        increment: Increment value.
        min_value: Minimum value.
        max_value: Maximum value.
        owned_by: Column that owns this sequence (e.g., 'users.id'), or None.
    """

    schema: str
    name: str
    data_type: str
    start_value: str | None = None
    increment: str | None = None
    min_value: str | None = None
    max_value: str | None = None
    owned_by: str | None = None


@dataclass
class OperatorMetadata:
    """Represents metadata for a custom database operator.

    Attributes:
        schema: Schema name containing the operator.
        name: Operator name/symbol (e.g., '&&', '->').
        left_type: Left operand type, or None for prefix operators.
        right_type: Right operand type, or None for postfix operators.
        result_type: Return type of the operator.
        function_name: Underlying function implementing the operator.
    """

    schema: str
    name: str
    left_type: str | None
    right_type: str | None
    result_type: str
    function_name: str


@dataclass
class SchemaMetadata:
    """Represents the complete metadata collected from a database.

    This is the main data structure passed between the MetadataCollector
    and the MarkdownGenerator.

    Attributes:
        database_name: Name of the database.
        schemas: List of schema names included in this metadata.
        tables: All tables with their column information.
        foreign_keys: All foreign key relationships (confirmed and inferred).
        views: All views with their definitions.
        functions: All functions and procedures.
        triggers: All triggers.
        types: All custom types (enum, composite, domain, etc.).
        sequences: All sequences.
        operators: All custom operators.
    """

    database_name: str
    schemas: list[str]
    tables: list[TableMetadata]
    foreign_keys: list[ForeignKeyMetadata]
    views: list[ViewMetadata]
    functions: list[FunctionMetadata]
    triggers: list[TriggerMetadata]
    types: list[TypeMetadata] = field(default_factory=list)
    sequences: list[SequenceMetadata] = field(default_factory=list)
    operators: list[OperatorMetadata] = field(default_factory=list)


@dataclass
class InferredFK:
    """Represents a foreign key relationship inferred by the FK Inference Engine.

    This is used internally by the FKInferenceEngine before converting to
    ForeignKeyMetadata with status='inferred'.

    Attributes:
        source_schema: Schema of the table containing the FK column.
        source_table: Name of the table containing the FK column.
        source_column: Column name that appears to reference another table.
        target_schema: Schema of the inferred referenced table.
        target_table: Name of the inferred referenced table.
        target_column: Column in the referenced table (typically 'id').
        confidence: Confidence level of the inference: 'high', 'medium', or 'low'.
        reason: Human-readable explanation of why this relationship was inferred.
    """

    source_schema: str
    source_table: str
    source_column: str
    target_schema: str
    target_table: str
    target_column: str
    confidence: str
    reason: str


@dataclass
class DbConfig:
    """Database connection configuration parsed from .env file.

    Attributes:
        connection: Database type identifier: 'pgsql' or 'mysql'.
        host: Database server hostname or IP address.
        port: Database server port number.
        username: Database username for authentication.
        password: Database password for authentication.
        databases: List of database names to process.
    """

    connection: str
    host: str
    port: int
    username: str
    password: str
    databases: list[str]
