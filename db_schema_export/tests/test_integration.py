"""Integration tests for the end-to-end pipeline.

Tests the complete flow: CLI → EnvParser → DBConnector → MetadataCollector
→ FKInference → MarkdownGenerator.

Validates:
- Full pipeline produces correct output files
- Multi-database flow generates multiple files
- Multi-schema flow prefixes schema names
- File naming follows `{database_name}_schema.md` pattern
- File overwrite behavior
- Requirements: 1.6, 3.1, 3.2, 9.10, 11.1, 11.2, 11.3, 12.1, 12.4
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from db_schema_export.cli import main
from db_schema_export.models import (
    ColumnMetadata,
    ForeignKeyMetadata,
    FunctionMetadata,
    SchemaMetadata,
    TableMetadata,
    TriggerMetadata,
    ViewMetadata,
)


def _create_env_file(tmp_path, databases=None, single_db=None):
    """Helper to create a .env file for testing."""
    env_file = tmp_path / ".env"
    content = (
        "DB_CONNECTION=pgsql\n"
        "DB_HOST=localhost\n"
        "DB_PORT=5432\n"
        "DB_USERNAME=testuser\n"
        "DB_PASSWORD=testpass\n"
    )
    if databases:
        content += f"DB_DATABASES={','.join(databases)}\n"
    elif single_db:
        content += f"DB_DATABASE={single_db}\n"
    else:
        content += "DB_DATABASE=testdb\n"
    env_file.write_text(content)
    return env_file


def _build_sample_metadata(database_name: str, schemas: list[str]) -> SchemaMetadata:
    """Build sample SchemaMetadata with realistic data for testing."""
    tables = [
        TableMetadata(
            schema=schemas[0],
            name="users",
            columns=[
                ColumnMetadata(
                    name="id",
                    data_type="integer",
                    is_nullable=False,
                    default_value="nextval('users_id_seq')",
                    is_primary_key=True,
                    comment="Primary key",
                ),
                ColumnMetadata(
                    name="name",
                    data_type="character varying",
                    is_nullable=False,
                    default_value=None,
                    max_length=255,
                    comment="User full name",
                ),
                ColumnMetadata(
                    name="email",
                    data_type="character varying",
                    is_nullable=False,
                    default_value=None,
                    max_length=255,
                ),
            ],
            comment="Application users table",
        ),
        TableMetadata(
            schema=schemas[0],
            name="orders",
            columns=[
                ColumnMetadata(
                    name="id",
                    data_type="integer",
                    is_nullable=False,
                    default_value="nextval('orders_id_seq')",
                    is_primary_key=True,
                ),
                ColumnMetadata(
                    name="user_id",
                    data_type="integer",
                    is_nullable=False,
                    default_value=None,
                    is_foreign_key=True,
                ),
                ColumnMetadata(
                    name="total",
                    data_type="numeric",
                    is_nullable=True,
                    default_value="0",
                ),
            ],
            comment="Customer orders",
        ),
    ]

    foreign_keys = [
        ForeignKeyMetadata(
            source_schema=schemas[0],
            source_table="orders",
            source_column="user_id",
            target_schema=schemas[0],
            target_table="users",
            target_column="id",
            status="confirmed",
        ),
    ]

    views = [
        ViewMetadata(
            schema=schemas[0],
            name="active_users",
            definition="SELECT id, name, email FROM users WHERE active = true",
        ),
    ]

    functions = [
        FunctionMetadata(
            schema=schemas[0],
            name="update_timestamp",
            arguments="",
            return_type="trigger",
            language="plpgsql",
            func_type="trigger function",
        ),
    ]

    triggers = [
        TriggerMetadata(
            schema=schemas[0],
            name="trg_update_timestamp",
            table_name="users",
            timing="BEFORE",
            event="UPDATE",
            function_name="EXECUTE FUNCTION update_timestamp()",
        ),
    ]

    return SchemaMetadata(
        database_name=database_name,
        schemas=schemas,
        tables=tables,
        foreign_keys=foreign_keys,
        views=views,
        functions=functions,
        triggers=triggers,
    )


def _build_multi_schema_metadata(database_name: str) -> SchemaMetadata:
    """Build metadata with multiple schemas for multi-schema testing."""
    schemas = ["public", "app"]
    tables = [
        TableMetadata(
            schema="public",
            name="users",
            columns=[
                ColumnMetadata(
                    name="id", data_type="integer", is_nullable=False,
                    default_value=None, is_primary_key=True,
                ),
                ColumnMetadata(
                    name="name", data_type="varchar", is_nullable=False,
                    default_value=None, max_length=100,
                ),
            ],
        ),
        TableMetadata(
            schema="app",
            name="settings",
            columns=[
                ColumnMetadata(
                    name="id", data_type="integer", is_nullable=False,
                    default_value=None, is_primary_key=True,
                ),
                ColumnMetadata(
                    name="user_id", data_type="integer", is_nullable=False,
                    default_value=None, is_foreign_key=True,
                ),
                ColumnMetadata(
                    name="key", data_type="varchar", is_nullable=False,
                    default_value=None, max_length=50,
                ),
            ],
        ),
    ]

    foreign_keys = [
        ForeignKeyMetadata(
            source_schema="app",
            source_table="settings",
            source_column="user_id",
            target_schema="public",
            target_table="users",
            target_column="id",
            status="confirmed",
        ),
    ]

    return SchemaMetadata(
        database_name=database_name,
        schemas=schemas,
        tables=tables,
        foreign_keys=foreign_keys,
        views=[],
        functions=[],
        triggers=[],
    )


class TestEndToEndSingleDatabase:
    """Test the full pipeline with a single database."""

    @patch("db_schema_export.cli.create_connector")
    def test_full_pipeline_produces_output_file(self, mock_create_connector, tmp_path):
        """Full pipeline should produce a correctly named output file."""
        env_file = _create_env_file(tmp_path, single_db="myapp_db")
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        mock_connector = MagicMock()
        mock_create_connector.return_value = mock_connector

        metadata = _build_sample_metadata("myapp_db", ["public"])

        with patch("db_schema_export.cli.MetadataCollector") as mock_collector_cls:
            mock_collector = MagicMock()
            mock_collector_cls.return_value = mock_collector
            mock_collector.get_schemas.return_value = ["public"]
            mock_collector.collect_all.return_value = metadata

            result = main([
                "--env", str(env_file),
                "--output", str(output_dir),
            ])

        assert result == 0

        # Verify file naming pattern: {database_name}_schema.md
        expected_file = output_dir / "myapp_db_schema.md"
        assert expected_file.exists()

    @patch("db_schema_export.cli.create_connector")
    def test_output_contains_expected_sections(self, mock_create_connector, tmp_path):
        """Output file should contain all expected sections: ERD, Tables, Views, etc."""
        env_file = _create_env_file(tmp_path, single_db="testdb")
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        mock_connector = MagicMock()
        mock_create_connector.return_value = mock_connector

        metadata = _build_sample_metadata("testdb", ["public"])

        with patch("db_schema_export.cli.MetadataCollector") as mock_collector_cls:
            mock_collector = MagicMock()
            mock_collector_cls.return_value = mock_collector
            mock_collector.get_schemas.return_value = ["public"]
            mock_collector.collect_all.return_value = metadata

            result = main([
                "--env", str(env_file),
                "--output", str(output_dir),
            ])

        assert result == 0

        output_file = output_dir / "testdb_schema.md"
        content = output_file.read_text(encoding="utf-8")

        # Check title
        assert "# testdb - Database Schema" in content

        # Check TOC
        assert "## Table of Contents" in content

        # Check ERD section with Mermaid
        assert "## ERD Diagram" in content
        assert "```mermaid" in content
        assert "erDiagram" in content

        # Check Tables section
        assert "## Tables" in content
        assert "### users" in content
        assert "### orders" in content

        # Check column details in table
        assert "| Column Name |" in content
        assert "user_id" in content

        # Check Views section
        assert "## Views" in content
        assert "active_users" in content

        # Check Functions section
        assert "## Functions/Procedures" in content
        assert "update_timestamp" in content

        # Check Triggers section
        assert "## Triggers" in content
        assert "trg_update_timestamp" in content

    @patch("db_schema_export.cli.create_connector")
    def test_erd_contains_relationships(self, mock_create_connector, tmp_path):
        """ERD section should contain relationship lines for FK constraints."""
        env_file = _create_env_file(tmp_path, single_db="testdb")
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        mock_connector = MagicMock()
        mock_create_connector.return_value = mock_connector

        metadata = _build_sample_metadata("testdb", ["public"])

        with patch("db_schema_export.cli.MetadataCollector") as mock_collector_cls:
            mock_collector = MagicMock()
            mock_collector_cls.return_value = mock_collector
            mock_collector.get_schemas.return_value = ["public"]
            mock_collector.collect_all.return_value = metadata

            result = main([
                "--env", str(env_file),
                "--output", str(output_dir),
            ])

        assert result == 0

        output_file = output_dir / "testdb_schema.md"
        content = output_file.read_text(encoding="utf-8")

        # ERD should contain both table entities
        assert "users {" in content
        assert "orders {" in content

        # ERD should contain the confirmed FK relationship (solid line --)
        assert "users" in content
        assert "orders" in content
        # Confirmed FK uses solid line notation
        assert "||--" in content

    @patch("db_schema_export.cli.create_connector")
    def test_file_overwrite_behavior(self, mock_create_connector, tmp_path):
        """Existing output file should be overwritten."""
        env_file = _create_env_file(tmp_path, single_db="testdb")
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Create an existing file with old content
        existing_file = output_dir / "testdb_schema.md"
        existing_file.write_text("OLD CONTENT THAT SHOULD BE OVERWRITTEN")

        mock_connector = MagicMock()
        mock_create_connector.return_value = mock_connector

        metadata = _build_sample_metadata("testdb", ["public"])

        with patch("db_schema_export.cli.MetadataCollector") as mock_collector_cls:
            mock_collector = MagicMock()
            mock_collector_cls.return_value = mock_collector
            mock_collector.get_schemas.return_value = ["public"]
            mock_collector.collect_all.return_value = metadata

            result = main([
                "--env", str(env_file),
                "--output", str(output_dir),
            ])

        assert result == 0

        content = existing_file.read_text(encoding="utf-8")
        # Old content should be gone
        assert "OLD CONTENT THAT SHOULD BE OVERWRITTEN" not in content
        # New content should be present
        assert "# testdb - Database Schema" in content


class TestEndToEndMultiDatabase:
    """Test the full pipeline with multiple databases (DB_DATABASES)."""

    @patch("db_schema_export.cli.create_connector")
    def test_multi_database_produces_multiple_files(
        self, mock_create_connector, tmp_path
    ):
        """Multiple databases should produce one file per database."""
        databases = ["app_dev", "app_staging", "app_prod"]
        env_file = _create_env_file(tmp_path, databases=databases)
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        mock_connector = MagicMock()
        mock_create_connector.return_value = mock_connector

        # Each database gets its own metadata
        def make_metadata(db_name):
            return _build_sample_metadata(db_name, ["public"])

        with patch("db_schema_export.cli.MetadataCollector") as mock_collector_cls:
            mock_collector = MagicMock()
            mock_collector_cls.return_value = mock_collector
            mock_collector.get_schemas.return_value = ["public"]

            # Return different metadata for each call
            mock_collector.collect_all.side_effect = [
                make_metadata("app_dev"),
                make_metadata("app_staging"),
                make_metadata("app_prod"),
            ]

            result = main([
                "--env", str(env_file),
                "--output", str(output_dir),
            ])

        assert result == 0

        # Verify one file per database with correct naming
        for db_name in databases:
            expected_file = output_dir / f"{db_name}_schema.md"
            assert expected_file.exists(), f"Expected file {expected_file} not found"
            content = expected_file.read_text(encoding="utf-8")
            assert f"# {db_name} - Database Schema" in content

    @patch("db_schema_export.cli.create_connector")
    def test_multi_database_files_are_independent(
        self, mock_create_connector, tmp_path
    ):
        """Each database file should only contain its own metadata."""
        databases = ["db_alpha", "db_beta"]
        env_file = _create_env_file(tmp_path, databases=databases)
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        mock_connector = MagicMock()
        mock_create_connector.return_value = mock_connector

        # Create distinct metadata for each database
        alpha_metadata = SchemaMetadata(
            database_name="db_alpha",
            schemas=["public"],
            tables=[
                TableMetadata(
                    schema="public",
                    name="alpha_table",
                    columns=[
                        ColumnMetadata(
                            name="id", data_type="integer",
                            is_nullable=False, default_value=None,
                            is_primary_key=True,
                        ),
                    ],
                ),
            ],
            foreign_keys=[],
            views=[],
            functions=[],
            triggers=[],
        )

        beta_metadata = SchemaMetadata(
            database_name="db_beta",
            schemas=["public"],
            tables=[
                TableMetadata(
                    schema="public",
                    name="beta_table",
                    columns=[
                        ColumnMetadata(
                            name="id", data_type="integer",
                            is_nullable=False, default_value=None,
                            is_primary_key=True,
                        ),
                    ],
                ),
            ],
            foreign_keys=[],
            views=[],
            functions=[],
            triggers=[],
        )

        with patch("db_schema_export.cli.MetadataCollector") as mock_collector_cls:
            mock_collector = MagicMock()
            mock_collector_cls.return_value = mock_collector
            mock_collector.get_schemas.return_value = ["public"]
            mock_collector.collect_all.side_effect = [alpha_metadata, beta_metadata]

            result = main([
                "--env", str(env_file),
                "--output", str(output_dir),
            ])

        assert result == 0

        # Alpha file should contain alpha_table but NOT beta_table
        alpha_content = (output_dir / "db_alpha_schema.md").read_text(encoding="utf-8")
        assert "alpha_table" in alpha_content
        assert "beta_table" not in alpha_content

        # Beta file should contain beta_table but NOT alpha_table
        beta_content = (output_dir / "db_beta_schema.md").read_text(encoding="utf-8")
        assert "beta_table" in beta_content
        assert "alpha_table" not in beta_content


class TestEndToEndMultiSchema:
    """Test the full pipeline with multiple schemas."""

    @patch("db_schema_export.cli.create_connector")
    def test_multi_schema_prefixes_names(self, mock_create_connector, tmp_path):
        """When multiple schemas exist, table names should be prefixed with schema."""
        env_file = _create_env_file(tmp_path, single_db="testdb")
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        mock_connector = MagicMock()
        mock_create_connector.return_value = mock_connector

        metadata = _build_multi_schema_metadata("testdb")

        with patch("db_schema_export.cli.MetadataCollector") as mock_collector_cls:
            mock_collector = MagicMock()
            mock_collector_cls.return_value = mock_collector
            mock_collector.get_schemas.return_value = ["public", "app"]
            mock_collector.collect_all.return_value = metadata

            result = main([
                "--env", str(env_file),
                "--output", str(output_dir),
            ])

        assert result == 0

        output_file = output_dir / "testdb_schema.md"
        content = output_file.read_text(encoding="utf-8")

        # Multi-schema should prefix table names with schema
        assert "### public.users" in content
        assert "### app.settings" in content

    @patch("db_schema_export.cli.create_connector")
    def test_single_schema_no_prefix(self, mock_create_connector, tmp_path):
        """When only one schema exists, table names should NOT be prefixed."""
        env_file = _create_env_file(tmp_path, single_db="testdb")
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        mock_connector = MagicMock()
        mock_create_connector.return_value = mock_connector

        metadata = _build_sample_metadata("testdb", ["public"])

        with patch("db_schema_export.cli.MetadataCollector") as mock_collector_cls:
            mock_collector = MagicMock()
            mock_collector_cls.return_value = mock_collector
            mock_collector.get_schemas.return_value = ["public"]
            mock_collector.collect_all.return_value = metadata

            result = main([
                "--env", str(env_file),
                "--output", str(output_dir),
            ])

        assert result == 0

        output_file = output_dir / "testdb_schema.md"
        content = output_file.read_text(encoding="utf-8")

        # Single schema should NOT prefix table names
        assert "### users" in content
        assert "### orders" in content
        # Should NOT have schema prefix
        assert "### public.users" not in content

    @patch("db_schema_export.cli.create_connector")
    def test_schema_filter_detects_non_system_schemas(
        self, mock_create_connector, tmp_path
    ):
        """Without --schema, tool should auto-detect non-system schemas."""
        env_file = _create_env_file(tmp_path, single_db="testdb")
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        mock_connector = MagicMock()
        mock_create_connector.return_value = mock_connector

        metadata = _build_sample_metadata("testdb", ["public"])

        with patch("db_schema_export.cli.MetadataCollector") as mock_collector_cls:
            mock_collector = MagicMock()
            mock_collector_cls.return_value = mock_collector
            # Simulates auto-detection of non-system schemas
            mock_collector.get_schemas.return_value = ["public"]
            mock_collector.collect_all.return_value = metadata

            result = main([
                "--env", str(env_file),
                "--output", str(output_dir),
            ])

        assert result == 0
        # get_schemas was called (auto-detect mode)
        mock_collector.get_schemas.assert_called_once()


class TestEndToEndFKInference:
    """Test FK inference integration in the pipeline."""

    @patch("db_schema_export.cli.create_connector")
    def test_fk_inference_produces_inferred_relationships(
        self, mock_create_connector, tmp_path
    ):
        """FK inference should add inferred relationships to the ERD."""
        env_file = _create_env_file(tmp_path, single_db="testdb")
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        mock_connector = MagicMock()
        mock_create_connector.return_value = mock_connector

        # Metadata with a column that can be inferred (category_id → categories)
        metadata = SchemaMetadata(
            database_name="testdb",
            schemas=["public"],
            tables=[
                TableMetadata(
                    schema="public",
                    name="products",
                    columns=[
                        ColumnMetadata(
                            name="id", data_type="integer",
                            is_nullable=False, default_value=None,
                            is_primary_key=True,
                        ),
                        ColumnMetadata(
                            name="category_id", data_type="integer",
                            is_nullable=True, default_value=None,
                        ),
                    ],
                ),
                TableMetadata(
                    schema="public",
                    name="categories",
                    columns=[
                        ColumnMetadata(
                            name="id", data_type="integer",
                            is_nullable=False, default_value=None,
                            is_primary_key=True,
                        ),
                        ColumnMetadata(
                            name="name", data_type="varchar",
                            is_nullable=False, default_value=None,
                        ),
                    ],
                ),
            ],
            foreign_keys=[],  # No explicit FKs
            views=[],
            functions=[],
            triggers=[],
        )

        with patch("db_schema_export.cli.MetadataCollector") as mock_collector_cls:
            mock_collector = MagicMock()
            mock_collector_cls.return_value = mock_collector
            mock_collector.get_schemas.return_value = ["public"]
            mock_collector.collect_all.return_value = metadata

            result = main([
                "--env", str(env_file),
                "--output", str(output_dir),
            ])

        assert result == 0

        output_file = output_dir / "testdb_schema.md"
        content = output_file.read_text(encoding="utf-8")

        # ERD should contain inferred relationship (dashed line ..)
        assert "categories" in content
        assert "products" in content
        # Inferred relationships use dashed lines
        assert ".." in content
        assert "inferred" in content

    @patch("db_schema_export.cli.create_connector")
    def test_no_infer_fk_disables_inference(self, mock_create_connector, tmp_path):
        """--no-infer-fk should prevent FK inference from running."""
        env_file = _create_env_file(tmp_path, single_db="testdb")
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        mock_connector = MagicMock()
        mock_create_connector.return_value = mock_connector

        metadata = SchemaMetadata(
            database_name="testdb",
            schemas=["public"],
            tables=[
                TableMetadata(
                    schema="public",
                    name="products",
                    columns=[
                        ColumnMetadata(
                            name="id", data_type="integer",
                            is_nullable=False, default_value=None,
                            is_primary_key=True,
                        ),
                        ColumnMetadata(
                            name="category_id", data_type="integer",
                            is_nullable=True, default_value=None,
                        ),
                    ],
                ),
                TableMetadata(
                    schema="public",
                    name="categories",
                    columns=[
                        ColumnMetadata(
                            name="id", data_type="integer",
                            is_nullable=False, default_value=None,
                            is_primary_key=True,
                        ),
                    ],
                ),
            ],
            foreign_keys=[],
            views=[],
            functions=[],
            triggers=[],
        )

        with patch("db_schema_export.cli.MetadataCollector") as mock_collector_cls:
            mock_collector = MagicMock()
            mock_collector_cls.return_value = mock_collector
            mock_collector.get_schemas.return_value = ["public"]
            mock_collector.collect_all.return_value = metadata

            result = main([
                "--env", str(env_file),
                "--output", str(output_dir),
                "--no-infer-fk",
            ])

        assert result == 0

        output_file = output_dir / "testdb_schema.md"
        content = output_file.read_text(encoding="utf-8")

        # No inferred relationship lines should appear in the ERD
        # (The legend may mention "inferred" but no actual dashed relationship lines)
        # Dashed lines in Mermaid use ".." notation for inferred FKs
        # Check that no relationship line with "inferred" label exists
        lines = content.split("\n")
        erd_relationship_lines = [
            line for line in lines
            if ".." in line and ": \"inferred\"" in line
        ]
        assert len(erd_relationship_lines) == 0, (
            f"Found inferred relationship lines when --no-infer-fk was set: "
            f"{erd_relationship_lines}"
        )


class TestEndToEndSectionsFiltering:
    """Test section filtering via --sections argument."""

    @patch("db_schema_export.cli.create_connector")
    def test_sections_filter_limits_output(self, mock_create_connector, tmp_path):
        """--sections should limit which sections appear in output."""
        env_file = _create_env_file(tmp_path, single_db="testdb")
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        mock_connector = MagicMock()
        mock_create_connector.return_value = mock_connector

        metadata = _build_sample_metadata("testdb", ["public"])

        with patch("db_schema_export.cli.MetadataCollector") as mock_collector_cls:
            mock_collector = MagicMock()
            mock_collector_cls.return_value = mock_collector
            mock_collector.get_schemas.return_value = ["public"]
            mock_collector.collect_all.return_value = metadata

            result = main([
                "--env", str(env_file),
                "--output", str(output_dir),
                "--sections", "erd,tables",
            ])

        assert result == 0

        output_file = output_dir / "testdb_schema.md"
        content = output_file.read_text(encoding="utf-8")

        # Included sections should be present
        assert "## ERD Diagram" in content
        assert "## Tables" in content

        # Excluded sections should NOT be present
        assert "## Views" not in content
        assert "## Functions/Procedures" not in content
        assert "## Triggers" not in content


class TestEndToEndErrorHandling:
    """Test error handling in the end-to-end flow."""

    @patch("db_schema_export.cli.create_connector")
    def test_partial_database_failure_returns_2(
        self, mock_create_connector, tmp_path
    ):
        """When some databases fail, exit code should be 2 (partial success)."""
        databases = ["good_db", "bad_db"]
        env_file = _create_env_file(tmp_path, databases=databases)
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        from db_schema_export.exceptions import DatabaseConnectionError

        # First connector succeeds, second fails
        mock_connector_good = MagicMock()
        mock_connector_bad = MagicMock()
        mock_connector_bad.connect.side_effect = DatabaseConnectionError(
            host="localhost", port=5432, database="bad_db",
            reason="Connection refused",
        )
        mock_create_connector.side_effect = [mock_connector_good, mock_connector_bad]

        metadata = _build_sample_metadata("good_db", ["public"])

        with patch("db_schema_export.cli.MetadataCollector") as mock_collector_cls:
            mock_collector = MagicMock()
            mock_collector_cls.return_value = mock_collector
            mock_collector.get_schemas.return_value = ["public"]
            mock_collector.collect_all.return_value = metadata

            result = main([
                "--env", str(env_file),
                "--output", str(output_dir),
            ])

        assert result == 2

        # Good database file should exist
        assert (output_dir / "good_db_schema.md").exists()
        # Bad database file should NOT exist
        assert not (output_dir / "bad_db_schema.md").exists()

    def test_missing_env_file_returns_1(self, tmp_path):
        """Missing .env file should return exit code 1."""
        result = main([
            "--env", str(tmp_path / "nonexistent.env"),
            "--output", str(tmp_path),
        ])
        assert result == 1
