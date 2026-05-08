"""FK Inference Engine for Database Schema Export Tool.

This module infers foreign key relationships between tables based on column
naming conventions. It supports 4 levels of matching with decreasing confidence:
1. Exact match (high): column `user_id` → table `user`
2. Plural match (medium): column `user_id` → table `users`
3. Suffix variant match (medium): column `store_id` → table `store_master`
4. Short name fuzzy match (low): column `uid` → table `users`

The engine also supports FK mapping file overrides to manually define or
correct inferred relationships.
"""

from __future__ import annotations

from db_schema_export.models import InferredFK, TableMetadata


# Fixed mapping dictionary for common short name abbreviations
SHORT_NAME_MAPPING: dict[str, list[str]] = {
    "uid": ["user", "users"],
    "cid": ["customer", "customers"],
    "pid": ["product", "products"],
    "oid": ["order", "orders"],
    "sid": ["store", "stores"],
    "tid": ["team", "teams"],
    "mid": ["member", "members"],
    "aid": ["account", "accounts"],
    "rid": ["role", "roles"],
    "gid": ["group", "groups"],
    "eid": ["employee", "employees"],
    "did": ["department", "departments"],
    "catid": ["category", "categories"],
    "orgid": ["organization", "organizations"],
}

# Suffixes to try for suffix variant matching
SUFFIX_VARIANTS: list[str] = ["_master", "_mst"]


class FKInferenceEngine:
    """Infers FK relationships based on column naming conventions.

    The engine processes all tables and their columns, attempting to match
    columns ending with `_id` (or known short names) to existing tables.

    Attributes:
        tables: List of table metadata to analyze.
        fk_mapping: Optional dictionary of manual FK overrides.
    """

    def __init__(
        self,
        tables: list[TableMetadata],
        fk_mapping: dict[str, str] | None = None,
    ) -> None:
        """Initialize the FK Inference Engine.

        Args:
            tables: List of TableMetadata objects to analyze for FK inference.
            fk_mapping: Optional dictionary mapping source columns to target
                columns. Keys are `{table.column}` or `{schema.table.column}`,
                values are `{referenced_table.referenced_column}`.
        """
        self.tables = tables
        self.fk_mapping = fk_mapping or {}
        # Build a lookup of table names by schema for fast matching
        self._table_lookup: dict[str, set[str]] = {}
        for table in tables:
            if table.schema not in self._table_lookup:
                self._table_lookup[table.schema] = set()
            self._table_lookup[table.schema].add(table.name)

    def infer_all(self) -> list[InferredFK]:
        """Run inference on all tables and return inferred relationships.

        Iterates through all tables and columns, attempting to match columns
        that look like foreign keys to their referenced tables. Applies
        mapping overrides at the end.

        Returns:
            List of InferredFK objects representing inferred relationships.
        """
        inferred: list[InferredFK] = []

        for table in self.tables:
            for column in table.columns:
                # Skip columns already marked as FK
                if column.is_foreign_key:
                    continue

                # Skip primary key columns
                if column.is_primary_key:
                    continue

                match = self._match_column_to_table(
                    column_name=column.name,
                    schema=table.schema,
                    source_table=table.name,
                )
                if match is not None:
                    inferred.append(match)

        # Apply mapping overrides
        inferred = self._apply_mapping_overrides(inferred)

        # Log inferred relationships
        for fk in inferred:
            print(
                f"  [FK Inferred] ({fk.confidence}) "
                f"{fk.source_schema}.{fk.source_table}.{fk.source_column} "
                f"→ {fk.target_schema}.{fk.target_table}.{fk.target_column} "
                f"| {fk.reason}"
            )

        return inferred

    def _match_column_to_table(
        self,
        column_name: str,
        schema: str,
        source_table: str,
    ) -> InferredFK | None:
        """Attempt to match a column name to a referenced table.

        Matching rules (in priority order):
        1. Exact match: {table_name}_id → table_name.id (confidence: high)
        2. Plural match: {singular}_id → {plural_table}.id (confidence: medium)
        3. Suffix variant match: {name}_id → {name}_master.id (confidence: medium)
        4. Short name fuzzy match: uid → users.id (confidence: low)

        Args:
            column_name: The column name to analyze.
            schema: The schema of the source table.
            source_table: The name of the source table.

        Returns:
            An InferredFK object if a match is found, None otherwise.
        """
        # Check if column ends with _id
        if column_name.endswith("_id"):
            prefix = column_name[:-3]  # Remove '_id' suffix
            if not prefix:
                return None

            # 1. Exact match: prefix matches a table name directly
            match = self._find_table_in_schema(prefix, schema)
            if match is not None and match != source_table:
                return InferredFK(
                    source_schema=schema,
                    source_table=source_table,
                    source_column=column_name,
                    target_schema=schema,
                    target_table=match,
                    target_column="id",
                    confidence="high",
                    reason=f"Exact match: column '{column_name}' → table '{match}'",
                )

            # 2. Plural match: try plural forms of the prefix
            plural_forms = self._get_plural_forms(prefix)
            for plural in plural_forms:
                match = self._find_table_in_schema(plural, schema)
                if match is not None and match != source_table:
                    return InferredFK(
                        source_schema=schema,
                        source_table=source_table,
                        source_column=column_name,
                        target_schema=schema,
                        target_table=match,
                        target_column="id",
                        confidence="medium",
                        reason=f"Plural match: column '{column_name}' → table '{match}'",
                    )

            # 3. Suffix variant match: try prefix_master, prefix_mst
            for suffix in SUFFIX_VARIANTS:
                variant = prefix + suffix
                match = self._find_table_in_schema(variant, schema)
                if match is not None and match != source_table:
                    return InferredFK(
                        source_schema=schema,
                        source_table=source_table,
                        source_column=column_name,
                        target_schema=schema,
                        target_table=match,
                        target_column="id",
                        confidence="medium",
                        reason=f"Suffix variant match: column '{column_name}' → table '{match}'",
                    )

            return None

        # 4. Short name fuzzy match for known abbreviations
        if column_name in SHORT_NAME_MAPPING:
            candidates = SHORT_NAME_MAPPING[column_name]
            for candidate in candidates:
                match = self._find_table_in_schema(candidate, schema)
                if match is not None and match != source_table:
                    return InferredFK(
                        source_schema=schema,
                        source_table=source_table,
                        source_column=column_name,
                        target_schema=schema,
                        target_table=match,
                        target_column="id",
                        confidence="low",
                        reason=f"Short name fuzzy match: column '{column_name}' → table '{match}'",
                    )

        return None

    def _find_table_in_schema(self, table_name: str, schema: str) -> str | None:
        """Find a table by name in the given schema.

        Args:
            table_name: The table name to search for.
            schema: The schema to search in.

        Returns:
            The table name if found, None otherwise.
        """
        tables_in_schema = self._table_lookup.get(schema, set())
        if table_name in tables_in_schema:
            return table_name
        return None

    def _get_plural_forms(self, singular: str) -> list[str]:
        """Generate possible plural forms of a singular word.

        Rules:
        - Words ending in 'y' (preceded by consonant): replace 'y' with 'ies'
        - Words ending in 's', 'x', 'z', 'ch', 'sh': add 'es'
        - Default: add 's'

        Args:
            singular: The singular form of the word.

        Returns:
            List of possible plural forms.
        """
        plurals: list[str] = []

        # Rule: words ending in 'y' preceded by a consonant → 'ies'
        if singular.endswith("y") and len(singular) > 1:
            char_before_y = singular[-2]
            if char_before_y not in "aeiou":
                plurals.append(singular[:-1] + "ies")

        # Rule: words ending in 's', 'x', 'z', 'ch', 'sh' → add 'es'
        if singular.endswith(("s", "x", "z", "ch", "sh")):
            plurals.append(singular + "es")

        # Default: add 's'
        plurals.append(singular + "s")

        return plurals

    def _apply_mapping_overrides(
        self, inferred: list[InferredFK]
    ) -> list[InferredFK]:
        """Apply FK mapping file overrides to inferred relationships.

        Mapping entries can add new relationships or override existing inferred
        ones. The mapping key format is `{table.column}` or
        `{schema.table.column}`, and the value is
        `{referenced_table.referenced_column}`.

        Args:
            inferred: List of currently inferred FK relationships.

        Returns:
            Updated list with mapping overrides applied.
        """
        if not self.fk_mapping:
            return inferred

        # Build a set of (schema.table.column) keys from inferred for quick lookup
        inferred_keys: dict[str, int] = {}
        for idx, fk in enumerate(inferred):
            # Key with schema
            key_full = f"{fk.source_schema}.{fk.source_table}.{fk.source_column}"
            inferred_keys[key_full] = idx
            # Key without schema
            key_short = f"{fk.source_table}.{fk.source_column}"
            inferred_keys[key_short] = idx

        result = list(inferred)

        for mapping_key, mapping_value in self.fk_mapping.items():
            # Parse the mapping key: {schema.table.column} or {table.column}
            source_parts = mapping_key.split(".")
            if len(source_parts) == 3:
                source_schema = source_parts[0]
                source_table = source_parts[1]
                source_column = source_parts[2]
            elif len(source_parts) == 2:
                source_table = source_parts[0]
                source_column = source_parts[1]
                # Try to find the schema from existing tables
                source_schema = self._find_schema_for_table(source_table)
            else:
                # Invalid format, skip
                continue

            # Parse the mapping value: {referenced_table.referenced_column}
            target_parts = mapping_value.split(".")
            if len(target_parts) == 2:
                target_table = target_parts[0]
                target_column = target_parts[1]
                target_schema = self._find_schema_for_table(target_table)
            elif len(target_parts) == 3:
                target_schema = target_parts[0]
                target_table = target_parts[1]
                target_column = target_parts[2]
            else:
                # Invalid format, skip
                continue

            # Create the override FK
            override_fk = InferredFK(
                source_schema=source_schema,
                source_table=source_table,
                source_column=source_column,
                target_schema=target_schema,
                target_table=target_table,
                target_column=target_column,
                confidence="high",
                reason=f"FK mapping override: '{mapping_key}' → '{mapping_value}'",
            )

            # Check if this overrides an existing inferred relationship
            key_full = f"{source_schema}.{source_table}.{source_column}"
            key_short = f"{source_table}.{source_column}"

            if key_full in inferred_keys:
                idx = inferred_keys[key_full]
                result[idx] = override_fk
            elif key_short in inferred_keys:
                idx = inferred_keys[key_short]
                result[idx] = override_fk
            else:
                # New relationship from mapping
                result.append(override_fk)

        return result

    def _find_schema_for_table(self, table_name: str) -> str:
        """Find the schema that contains a given table name.

        If the table is found in multiple schemas, returns the first match.
        If not found, defaults to 'public'.

        Args:
            table_name: The table name to search for.

        Returns:
            The schema name containing the table, or 'public' as default.
        """
        for schema, tables in self._table_lookup.items():
            if table_name in tables:
                return schema
        return "public"
