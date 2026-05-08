"""Metadata collector module for Database Schema Export Tool.

This module queries database metadata from PostgreSQL using information_schema
and pg_catalog system catalogs. It collects tables, columns, primary keys,
foreign keys, views, functions, and triggers.

Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8, 9.9, 12.1
"""

from __future__ import annotations

import logging

from db_schema_export.db_connector import DatabaseConnector
from db_schema_export.exceptions import MetadataQueryError
from db_schema_export.models import (
    ColumnMetadata,
    ForeignKeyMetadata,
    FunctionMetadata,
    OperatorMetadata,
    SchemaMetadata,
    SequenceMetadata,
    TableMetadata,
    TriggerMetadata,
    TypeMetadata,
    ViewMetadata,
)

logger = logging.getLogger(__name__)


class MetadataCollector:
    """Collects schema metadata from database using information_schema queries.

    This class queries PostgreSQL system catalogs to retrieve comprehensive
    metadata about database objects including tables, columns, constraints,
    views, functions, and triggers.

    Attributes:
        connector: A DatabaseConnector instance used to execute queries.
    """

    def __init__(self, connector: DatabaseConnector) -> None:
        """Initialize MetadataCollector with a database connector.

        Args:
            connector: A connected DatabaseConnector instance.
        """
        self.connector = connector

    def get_schemas(self) -> list[str]:
        """Get all non-system schemas from the database.

        Excludes system schemas: pg_catalog, information_schema, pg_toast,
        and temporary schemas (pg_temp_*, pg_toast_temp_*).

        Uses pg_catalog.pg_namespace instead of information_schema.schemata
        to avoid permission-based filtering that hides schemas the user
        can actually access.

        Returns:
            Sorted list of non-system schema names.

        Raises:
            MetadataQueryError: If the schema query fails.
        """
        query = """
            SELECT nspname AS schema_name
            FROM pg_catalog.pg_namespace
            WHERE nspname NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
              AND nspname NOT LIKE 'pg_temp_%%'
              AND nspname NOT LIKE 'pg_toast_temp_%%'
            ORDER BY nspname;
        """
        try:
            rows = self.connector.execute_query(query)
            return [row["schema_name"] for row in rows]
        except Exception as e:
            raise MetadataQueryError(
                query_type="schemas",
                reason=str(e),
            ) from e

    def get_tables(self, schemas: list[str]) -> list[TableMetadata]:
        """Get all tables in specified schemas with comments.

        Uses pg_catalog.pg_class directly instead of information_schema.tables
        to avoid permission-based filtering that hides tables the user can
        actually query.

        Args:
            schemas: List of schema names to query.

        Returns:
            List of TableMetadata objects (without columns populated).

        Raises:
            MetadataQueryError: If the tables query fails.
        """
        query = """
            SELECT n.nspname AS table_schema,
                   c.relname AS table_name,
                   pg_catalog.obj_description(c.oid) AS table_comment
            FROM pg_catalog.pg_class c
            JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = ANY(%s)
              AND c.relkind = 'r'
            ORDER BY n.nspname, c.relname;
        """
        try:
            rows = self.connector.execute_query(query, (schemas,))
            return [
                TableMetadata(
                    schema=row["table_schema"],
                    name=row["table_name"],
                    comment=row.get("table_comment"),
                )
                for row in rows
            ]
        except Exception as e:
            raise MetadataQueryError(
                query_type="tables",
                reason=str(e),
            ) from e

    def get_columns(self, schema: str, table: str) -> list[ColumnMetadata]:
        """Get column details for a specific table.

        Uses pg_catalog.pg_attribute directly instead of information_schema.columns
        to avoid permission-based filtering.

        Args:
            schema: Schema name containing the table.
            table: Table name to get columns for.

        Returns:
            List of ColumnMetadata objects ordered by ordinal position.

        Raises:
            MetadataQueryError: If the columns query fails.
        """
        query = """
            SELECT a.attname AS column_name,
                   pg_catalog.format_type(a.atttypid, a.atttypmod) AS data_type,
                   NOT a.attnotnull AS is_nullable,
                   pg_catalog.pg_get_expr(d.adbin, d.adrelid) AS column_default,
                   pg_catalog.col_description(c.oid, a.attnum) AS column_comment,
                   CASE WHEN a.atttypmod > 0 AND t.typname IN ('varchar', 'bpchar')
                        THEN a.atttypmod - 4
                        ELSE NULL
                   END AS character_maximum_length
            FROM pg_catalog.pg_attribute a
            JOIN pg_catalog.pg_class c ON c.oid = a.attrelid
            JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
            JOIN pg_catalog.pg_type t ON t.oid = a.atttypid
            LEFT JOIN pg_catalog.pg_attrdef d ON d.adrelid = a.attrelid
                AND d.adnum = a.attnum
            WHERE n.nspname = %s
              AND c.relname = %s
              AND a.attnum > 0
              AND NOT a.attisdropped
            ORDER BY a.attnum;
        """
        try:
            rows = self.connector.execute_query(query, (schema, table))
            columns = []
            for row in rows:
                # pg_attribute returns is_nullable as boolean (NOT attnotnull)
                is_nullable = bool(row["is_nullable"])
                max_length = row.get("character_maximum_length")
                if max_length is not None:
                    max_length = int(max_length)

                columns.append(
                    ColumnMetadata(
                        name=row["column_name"],
                        data_type=row["data_type"],
                        is_nullable=is_nullable,
                        default_value=row.get("column_default"),
                        comment=row.get("column_comment"),
                        max_length=max_length,
                    )
                )
            return columns
        except Exception as e:
            raise MetadataQueryError(
                query_type="columns",
                reason=str(e),
                schema=schema,
            ) from e

    def get_primary_keys(self, schemas: list[str]) -> dict[str, list[str]]:
        """Get primary key columns grouped by schema.table.

        Uses pg_catalog directly to avoid information_schema permission issues.

        Args:
            schemas: List of schema names to query.

        Returns:
            Dictionary mapping "schema.table" to list of PK column names.

        Raises:
            MetadataQueryError: If the primary keys query fails.
        """
        query = """
            SELECT n.nspname AS table_schema,
                   c.relname AS table_name,
                   a.attname AS column_name
            FROM pg_catalog.pg_index i
            JOIN pg_catalog.pg_class c ON c.oid = i.indrelid
            JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
            JOIN pg_catalog.pg_attribute a ON a.attrelid = c.oid
                AND a.attnum = ANY(i.indkey)
            WHERE i.indisprimary
              AND n.nspname = ANY(%s);
        """
        try:
            rows = self.connector.execute_query(query, (schemas,))
            pk_map: dict[str, list[str]] = {}
            for row in rows:
                key = f"{row['table_schema']}.{row['table_name']}"
                if key not in pk_map:
                    pk_map[key] = []
                pk_map[key].append(row["column_name"])
            return pk_map
        except Exception as e:
            raise MetadataQueryError(
                query_type="primary_keys",
                reason=str(e),
            ) from e

    def get_foreign_keys(self, schemas: list[str]) -> list[ForeignKeyMetadata]:
        """Get explicit FK constraints from the database.

        Uses pg_catalog directly to avoid information_schema permission issues.

        Args:
            schemas: List of schema names to query.

        Returns:
            List of ForeignKeyMetadata objects with status='confirmed'.

        Raises:
            MetadataQueryError: If the foreign keys query fails.
        """
        query = """
            SELECT
                n1.nspname AS table_schema,
                c1.relname AS table_name,
                a1.attname AS column_name,
                n2.nspname AS referenced_schema,
                c2.relname AS referenced_table,
                a2.attname AS referenced_column
            FROM pg_catalog.pg_constraint con
            JOIN pg_catalog.pg_class c1 ON c1.oid = con.conrelid
            JOIN pg_catalog.pg_namespace n1 ON n1.oid = c1.relnamespace
            JOIN pg_catalog.pg_class c2 ON c2.oid = con.confrelid
            JOIN pg_catalog.pg_namespace n2 ON n2.oid = c2.relnamespace
            JOIN pg_catalog.pg_attribute a1 ON a1.attrelid = con.conrelid
                AND a1.attnum = ANY(con.conkey)
            JOIN pg_catalog.pg_attribute a2 ON a2.attrelid = con.confrelid
                AND a2.attnum = ANY(con.confkey)
            WHERE con.contype = 'f'
              AND n1.nspname = ANY(%s);
        """
        try:
            rows = self.connector.execute_query(query, (schemas,))
            return [
                ForeignKeyMetadata(
                    source_schema=row["table_schema"],
                    source_table=row["table_name"],
                    source_column=row["column_name"],
                    target_schema=row["referenced_schema"],
                    target_table=row["referenced_table"],
                    target_column=row["referenced_column"],
                    status="confirmed",
                )
                for row in rows
            ]
        except Exception as e:
            raise MetadataQueryError(
                query_type="foreign_keys",
                reason=str(e),
            ) from e

    def get_views(self, schemas: list[str]) -> list[ViewMetadata]:
        """Get view definitions from the database.

        Uses pg_catalog directly to avoid information_schema permission issues.

        Args:
            schemas: List of schema names to query.

        Returns:
            List of ViewMetadata objects.

        Raises:
            MetadataQueryError: If the views query fails.
        """
        query = """
            SELECT n.nspname AS table_schema,
                   c.relname AS table_name,
                   pg_catalog.pg_get_viewdef(c.oid, true) AS view_definition
            FROM pg_catalog.pg_class c
            JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = ANY(%s)
              AND c.relkind = 'v'
            ORDER BY n.nspname, c.relname;
        """
        try:
            rows = self.connector.execute_query(query, (schemas,))
            return [
                ViewMetadata(
                    schema=row["table_schema"],
                    name=row["table_name"],
                    definition=row.get("view_definition") or "",
                )
                for row in rows
            ]
        except Exception as e:
            raise MetadataQueryError(
                query_type="views",
                reason=str(e),
            ) from e

    def get_functions(self, schemas: list[str]) -> list[FunctionMetadata]:
        """Get function/procedure metadata from pg_catalog.

        Queries pg_proc joined with pg_namespace and pg_language to retrieve
        function signatures, return types, and language information.

        Args:
            schemas: List of schema names to query.

        Returns:
            List of FunctionMetadata objects.

        Raises:
            MetadataQueryError: If the functions query fails.
        """
        query = """
            SELECT n.nspname as schema, p.proname as name,
                   pg_catalog.pg_get_function_arguments(p.oid) as arguments,
                   pg_catalog.pg_get_function_result(p.oid) as return_type,
                   l.lanname as language,
                   CASE p.prokind
                       WHEN 'f' THEN 'function'
                       WHEN 'p' THEN 'procedure'
                       WHEN 'w' THEN 'window'
                   END as type
            FROM pg_catalog.pg_proc p
            JOIN pg_catalog.pg_namespace n ON n.oid = p.pronamespace
            JOIN pg_catalog.pg_language l ON l.oid = p.prolang
            WHERE n.nspname = ANY(%s)
              AND p.proname NOT LIKE 'pg_%%'
            ORDER BY n.nspname, p.proname;
        """
        try:
            rows = self.connector.execute_query(query, (schemas,))
            functions = []
            for row in rows:
                # Determine func_type: if return_type is 'trigger', classify as trigger function
                return_type = row.get("return_type") or ""
                func_type = row.get("type") or "function"
                if return_type.lower() == "trigger":
                    func_type = "trigger function"

                functions.append(
                    FunctionMetadata(
                        schema=row["schema"],
                        name=row["name"],
                        arguments=row.get("arguments") or "",
                        return_type=return_type,
                        language=row.get("language") or "",
                        func_type=func_type,
                    )
                )
            return functions
        except Exception as e:
            raise MetadataQueryError(
                query_type="functions",
                reason=str(e),
            ) from e

    def get_triggers(self, schemas: list[str]) -> list[TriggerMetadata]:
        """Get trigger metadata from pg_catalog.

        Uses pg_catalog.pg_trigger directly to avoid information_schema
        permission issues.

        Args:
            schemas: List of schema names to query.

        Returns:
            List of TriggerMetadata objects.

        Raises:
            MetadataQueryError: If the triggers query fails.
        """
        query = """
            SELECT n.nspname AS trigger_schema,
                   t.tgname AS trigger_name,
                   c.relname AS event_object_table,
                   CASE
                       WHEN (t.tgtype & 2) != 0 THEN 'BEFORE'
                       WHEN (t.tgtype & 64) != 0 THEN 'INSTEAD OF'
                       ELSE 'AFTER'
                   END AS action_timing,
                   CASE
                       WHEN (t.tgtype & 4) != 0 AND (t.tgtype & 8) != 0 AND (t.tgtype & 16) != 0
                           THEN 'INSERT OR UPDATE OR DELETE'
                       WHEN (t.tgtype & 4) != 0 AND (t.tgtype & 8) != 0
                           THEN 'INSERT OR DELETE'
                       WHEN (t.tgtype & 4) != 0 AND (t.tgtype & 16) != 0
                           THEN 'INSERT OR UPDATE'
                       WHEN (t.tgtype & 8) != 0 AND (t.tgtype & 16) != 0
                           THEN 'DELETE OR UPDATE'
                       WHEN (t.tgtype & 4) != 0 THEN 'INSERT'
                       WHEN (t.tgtype & 8) != 0 THEN 'DELETE'
                       WHEN (t.tgtype & 16) != 0 THEN 'UPDATE'
                       ELSE 'UNKNOWN'
                   END AS event_manipulation,
                   p.proname AS function_name
            FROM pg_catalog.pg_trigger t
            JOIN pg_catalog.pg_class c ON c.oid = t.tgrelid
            JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
            JOIN pg_catalog.pg_proc p ON p.oid = t.tgfoid
            WHERE NOT t.tgisinternal
              AND n.nspname = ANY(%s)
            ORDER BY c.relname, t.tgname;
        """
        try:
            rows = self.connector.execute_query(query, (schemas,))
            return [
                TriggerMetadata(
                    schema=row["trigger_schema"],
                    name=row["trigger_name"],
                    table_name=row["event_object_table"],
                    timing=row["action_timing"],
                    event=row["event_manipulation"],
                    function_name=row.get("function_name") or "",
                )
                for row in rows
            ]
        except Exception as e:
            raise MetadataQueryError(
                query_type="triggers",
                reason=str(e),
            ) from e

    def get_types(self, schemas: list[str]) -> list[TypeMetadata]:
        """Get custom type definitions from the database.

        Retrieves enum types, composite types, domain types, and range types.

        Args:
            schemas: List of schema names to query.

        Returns:
            List of TypeMetadata objects.

        Raises:
            MetadataQueryError: If the types query fails.
        """
        query = """
            SELECT n.nspname AS schema,
                   t.typname AS name,
                   CASE t.typtype
                       WHEN 'e' THEN 'enum'
                       WHEN 'c' THEN 'composite'
                       WHEN 'd' THEN 'domain'
                       WHEN 'r' THEN 'range'
                       ELSE 'base'
                   END AS type_type,
                   CASE t.typtype
                       WHEN 'e' THEN (
                           SELECT string_agg(e.enumlabel, ', ' ORDER BY e.enumsortorder)
                           FROM pg_catalog.pg_enum e
                           WHERE e.enumtypid = t.oid
                       )
                       WHEN 'd' THEN pg_catalog.format_type(t.typbasetype, t.typtypmod)
                       ELSE ''
                   END AS definition
            FROM pg_catalog.pg_type t
            JOIN pg_catalog.pg_namespace n ON n.oid = t.typnamespace
            WHERE n.nspname = ANY(%s)
              AND t.typtype IN ('e', 'c', 'd', 'r')
              AND NOT EXISTS (
                  SELECT 1 FROM pg_catalog.pg_class c
                  WHERE c.reltype = t.oid AND c.relkind != 'c'
              )
            ORDER BY n.nspname, t.typname;
        """
        try:
            rows = self.connector.execute_query(query, (schemas,))
            return [
                TypeMetadata(
                    schema=row["schema"],
                    name=row["name"],
                    type_type=row["type_type"],
                    definition=row.get("definition") or "",
                )
                for row in rows
            ]
        except Exception as e:
            raise MetadataQueryError(
                query_type="types",
                reason=str(e),
            ) from e

    def get_sequences(self, schemas: list[str]) -> list[SequenceMetadata]:
        """Get sequence metadata from the database.

        Args:
            schemas: List of schema names to query.

        Returns:
            List of SequenceMetadata objects.

        Raises:
            MetadataQueryError: If the sequences query fails.
        """
        query = """
            SELECT n.nspname AS schema,
                   c.relname AS name,
                   pg_catalog.format_type(s.seqtypid, NULL) AS data_type,
                   s.seqstart::text AS start_value,
                   s.seqincrement::text AS increment,
                   s.seqmin::text AS min_value,
                   s.seqmax::text AS max_value,
                   CASE WHEN d.refobjid IS NOT NULL
                        THEN (SELECT relname FROM pg_catalog.pg_class WHERE oid = d.refobjid)
                             || '.' ||
                             (SELECT attname FROM pg_catalog.pg_attribute
                              WHERE attrelid = d.refobjid AND attnum = d.refobjsubid)
                        ELSE NULL
                   END AS owned_by
            FROM pg_catalog.pg_sequence s
            JOIN pg_catalog.pg_class c ON c.oid = s.seqrelid
            JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
            LEFT JOIN pg_catalog.pg_depend d ON d.objid = c.oid
                AND d.deptype = 'a'
                AND d.classid = 'pg_class'::regclass
            WHERE n.nspname = ANY(%s)
            ORDER BY n.nspname, c.relname;
        """
        try:
            rows = self.connector.execute_query(query, (schemas,))
            return [
                SequenceMetadata(
                    schema=row["schema"],
                    name=row["name"],
                    data_type=row.get("data_type") or "bigint",
                    start_value=row.get("start_value"),
                    increment=row.get("increment"),
                    min_value=row.get("min_value"),
                    max_value=row.get("max_value"),
                    owned_by=row.get("owned_by"),
                )
                for row in rows
            ]
        except Exception as e:
            raise MetadataQueryError(
                query_type="sequences",
                reason=str(e),
            ) from e

    def get_operators(self, schemas: list[str]) -> list[OperatorMetadata]:
        """Get custom operator metadata from the database.

        Excludes system operators (pg_catalog).

        Args:
            schemas: List of schema names to query.

        Returns:
            List of OperatorMetadata objects.

        Raises:
            MetadataQueryError: If the operators query fails.
        """
        query = """
            SELECT n.nspname AS schema,
                   o.oprname AS name,
                   CASE WHEN o.oprleft != 0
                        THEN pg_catalog.format_type(o.oprleft, NULL)
                        ELSE NULL
                   END AS left_type,
                   CASE WHEN o.oprright != 0
                        THEN pg_catalog.format_type(o.oprright, NULL)
                        ELSE NULL
                   END AS right_type,
                   pg_catalog.format_type(o.oprresult, NULL) AS result_type,
                   p.proname AS function_name
            FROM pg_catalog.pg_operator o
            JOIN pg_catalog.pg_namespace n ON n.oid = o.oprnamespace
            JOIN pg_catalog.pg_proc p ON p.oid = o.oprcode
            WHERE n.nspname = ANY(%s)
            ORDER BY n.nspname, o.oprname;
        """
        try:
            rows = self.connector.execute_query(query, (schemas,))
            return [
                OperatorMetadata(
                    schema=row["schema"],
                    name=row["name"],
                    left_type=row.get("left_type"),
                    right_type=row.get("right_type"),
                    result_type=row["result_type"],
                    function_name=row["function_name"],
                )
                for row in rows
            ]
        except Exception as e:
            raise MetadataQueryError(
                query_type="operators",
                reason=str(e),
            ) from e

    def collect_all(self, schemas: list[str], database_name: str) -> SchemaMetadata:
        """Collect all metadata for specified schemas.

        This is the main entry point that orchestrates all metadata queries.
        It handles graceful degradation - if one query type fails, it logs
        a warning and continues with others.

        Args:
            schemas: List of schema names to collect metadata for.
            database_name: Name of the database being queried.

        Returns:
            SchemaMetadata object containing all collected metadata.
        """
        tables: list[TableMetadata] = []
        foreign_keys: list[ForeignKeyMetadata] = []
        views: list[ViewMetadata] = []
        functions: list[FunctionMetadata] = []
        triggers: list[TriggerMetadata] = []
        types: list[TypeMetadata] = []
        sequences: list[SequenceMetadata] = []
        operators: list[OperatorMetadata] = []

        # 1. Get tables
        try:
            tables = self.get_tables(schemas)
        except MetadataQueryError as e:
            logger.warning("Failed to collect tables: %s", e.reason)

        # 2. For each table, get columns
        for table in tables:
            try:
                table.columns = self.get_columns(table.schema, table.name)
            except MetadataQueryError as e:
                logger.warning(
                    "Failed to collect columns for %s.%s: %s",
                    table.schema,
                    table.name,
                    e.reason,
                )

        # 3. Get primary keys and mark columns accordingly
        try:
            pk_map = self.get_primary_keys(schemas)
            for table in tables:
                key = f"{table.schema}.{table.name}"
                pk_columns = pk_map.get(key, [])
                for column in table.columns:
                    if column.name in pk_columns:
                        column.is_primary_key = True
        except MetadataQueryError as e:
            logger.warning("Failed to collect primary keys: %s", e.reason)

        # 4. Get foreign keys and mark columns accordingly
        try:
            foreign_keys = self.get_foreign_keys(schemas)
            # Mark FK columns on tables
            fk_columns: dict[str, set[str]] = {}
            for fk in foreign_keys:
                key = f"{fk.source_schema}.{fk.source_table}"
                if key not in fk_columns:
                    fk_columns[key] = set()
                fk_columns[key].add(fk.source_column)

            for table in tables:
                key = f"{table.schema}.{table.name}"
                table_fk_cols = fk_columns.get(key, set())
                for column in table.columns:
                    if column.name in table_fk_cols:
                        column.is_foreign_key = True
        except MetadataQueryError as e:
            logger.warning("Failed to collect foreign keys: %s", e.reason)

        # 5. Get views
        try:
            views = self.get_views(schemas)
        except MetadataQueryError as e:
            logger.warning("Failed to collect views: %s", e.reason)

        # 6. Get functions
        try:
            functions = self.get_functions(schemas)
        except MetadataQueryError as e:
            logger.warning("Failed to collect functions: %s", e.reason)

        # 7. Get triggers
        try:
            triggers = self.get_triggers(schemas)
        except MetadataQueryError as e:
            logger.warning("Failed to collect triggers: %s", e.reason)

        # 8. Get types
        try:
            types = self.get_types(schemas)
        except MetadataQueryError as e:
            logger.warning("Failed to collect types: %s", e.reason)

        # 9. Get sequences
        try:
            sequences = self.get_sequences(schemas)
        except MetadataQueryError as e:
            logger.warning("Failed to collect sequences: %s", e.reason)

        # 10. Get operators
        try:
            operators = self.get_operators(schemas)
        except MetadataQueryError as e:
            logger.warning("Failed to collect operators: %s", e.reason)

        return SchemaMetadata(
            database_name=database_name,
            schemas=schemas,
            tables=tables,
            foreign_keys=foreign_keys,
            views=views,
            functions=functions,
            triggers=triggers,
            types=types,
            sequences=sequences,
            operators=operators,
        )
