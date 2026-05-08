"""Unit tests for cli.py module.

Tests argument parsing, FK map validation, section/schema parsing,
and the main orchestration function with mocked dependencies.
"""

from __future__ import annotations

import json
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from db_schema_export.cli import (
    _parse_schemas,
    _parse_sections,
    _validate_fk_map,
    main,
    parse_args,
)
from db_schema_export.exceptions import (
    DatabaseConnectionError,
    FKMapFileNotFoundError,
    FKMapParseError,
)


class TestParseArgs:
    """Tests for parse_args() function."""

    def test_default_values(self):
        """All defaults should be applied when no args provided."""
        args = parse_args([])
        assert args.output == "."
        assert args.env == ".env"
        assert args.schema is None
        assert args.sections is None
        assert args.no_infer_fk is False
        assert args.fk_map is None

    def test_output_argument(self):
        """--output should set the output directory."""
        args = parse_args(["--output", "/tmp/docs"])
        assert args.output == "/tmp/docs"

    def test_env_argument(self):
        """--env should set the .env file path."""
        args = parse_args(["--env", "/path/to/.env.production"])
        assert args.env == "/path/to/.env.production"

    def test_schema_argument(self):
        """--schema should accept comma-separated schema list."""
        args = parse_args(["--schema", "public,salesforce"])
        assert args.schema == "public,salesforce"

    def test_sections_argument(self):
        """--sections should accept comma-separated sections list."""
        args = parse_args(["--sections", "erd,tables"])
        assert args.sections == "erd,tables"

    def test_no_infer_fk_flag(self):
        """--no-infer-fk should set the flag to True."""
        args = parse_args(["--no-infer-fk"])
        assert args.no_infer_fk is True

    def test_fk_map_argument(self):
        """--fk-map should set the FK mapping file path."""
        args = parse_args(["--fk-map", "fk_mapping.json"])
        assert args.fk_map == "fk_mapping.json"

    def test_all_arguments_combined(self):
        """All arguments should work together."""
        args = parse_args([
            "--output", "output_dir",
            "--env", "custom.env",
            "--schema", "public,app",
            "--sections", "erd,tables,views",
            "--no-infer-fk",
            "--fk-map", "map.json",
        ])
        assert args.output == "output_dir"
        assert args.env == "custom.env"
        assert args.schema == "public,app"
        assert args.sections == "erd,tables,views"
        assert args.no_infer_fk is True
        assert args.fk_map == "map.json"


class TestValidateFkMap:
    """Tests for _validate_fk_map() function."""

    def test_file_not_found(self):
        """Should raise FKMapFileNotFoundError for missing file."""
        with pytest.raises(FKMapFileNotFoundError):
            _validate_fk_map("/nonexistent/path/fk_map.json")

    def test_valid_json(self, tmp_path):
        """Should parse valid JSON file successfully."""
        fk_file = tmp_path / "fk_map.json"
        fk_file.write_text('{"users.org_id": "organizations.id"}')

        result = _validate_fk_map(str(fk_file))
        assert result == {"users.org_id": "organizations.id"}

    def test_invalid_json(self, tmp_path):
        """Should raise FKMapParseError for invalid JSON."""
        fk_file = tmp_path / "fk_map.json"
        fk_file.write_text("{invalid json content")

        with pytest.raises(FKMapParseError):
            _validate_fk_map(str(fk_file))

    def test_non_dict_json(self, tmp_path):
        """Should raise FKMapParseError when JSON is not a dict."""
        fk_file = tmp_path / "fk_map.json"
        fk_file.write_text('["not", "a", "dict"]')

        with pytest.raises(FKMapParseError):
            _validate_fk_map(str(fk_file))

    def test_empty_dict(self, tmp_path):
        """Should accept empty dict as valid FK mapping."""
        fk_file = tmp_path / "fk_map.json"
        fk_file.write_text("{}")

        result = _validate_fk_map(str(fk_file))
        assert result == {}


class TestParseSections:
    """Tests for _parse_sections() function."""

    def test_none_returns_all_sections(self):
        """None input should return all valid sections."""
        result = _parse_sections(None)
        assert result == ["erd", "tables", "views", "functions", "triggers", "types", "sequences", "operators"]

    def test_valid_sections(self):
        """Valid section names should be returned as-is."""
        result = _parse_sections("erd,tables")
        assert result == ["erd", "tables"]

    def test_invalid_sections_ignored(self, capsys):
        """Invalid section names should be ignored with a warning."""
        result = _parse_sections("erd,invalid,tables")
        assert result == ["erd", "tables"]
        captured = capsys.readouterr()
        assert "invalid" in captured.err.lower()

    def test_all_invalid_returns_all(self, capsys):
        """If all sections are invalid, return all valid sections."""
        result = _parse_sections("foo,bar")
        assert result == ["erd", "tables", "views", "functions", "triggers", "types", "sequences", "operators"]

    def test_whitespace_trimming(self):
        """Whitespace around section names should be trimmed."""
        result = _parse_sections(" erd , tables , views ")
        assert result == ["erd", "tables", "views"]


class TestParseSchemas:
    """Tests for _parse_schemas() function."""

    def test_none_returns_none(self):
        """None input should return None (auto-detect)."""
        result = _parse_schemas(None)
        assert result is None

    def test_comma_separated(self):
        """Should parse comma-separated schema names."""
        result = _parse_schemas("public,salesforce")
        assert result == ["public", "salesforce"]

    def test_whitespace_trimming(self):
        """Whitespace around schema names should be trimmed."""
        result = _parse_schemas(" public , salesforce ")
        assert result == ["public", "salesforce"]

    def test_empty_string_returns_none(self):
        """Empty string should return None."""
        result = _parse_schemas("")
        assert result is None


class TestMain:
    """Tests for main() orchestration function."""

    def test_env_file_not_found_returns_1(self, tmp_path):
        """Should return exit code 1 when .env file doesn't exist."""
        env_path = str(tmp_path / "nonexistent.env")
        result = main(["--env", env_path])
        assert result == 1

    def test_invalid_fk_map_warns_and_continues(self, tmp_path, capsys):
        """Should warn and continue when --fk-map file doesn't exist."""
        # Create a valid .env file
        env_file = tmp_path / ".env"
        env_file.write_text(
            "DB_CONNECTION=pgsql\n"
            "DB_HOST=localhost\n"
            "DB_PORT=5432\n"
            "DB_USERNAME=user\n"
            "DB_PASSWORD=pass\n"
            "DB_DATABASE=testdb\n"
        )

        result = main([
            "--env", str(env_file),
            "--fk-map", "/nonexistent/fk_map.json",
        ])
        # Should NOT return 1 (fatal) - it continues without FK mapping
        # It will fail on DB connection (exit 1) but the fk-map itself is just a warning
        captured = capsys.readouterr()
        assert "FK mapping file not found" in captured.err

    def test_invalid_fk_map_json_returns_1(self, tmp_path):
        """Should return exit code 1 when --fk-map has invalid JSON."""
        env_file = tmp_path / ".env"
        env_file.write_text(
            "DB_CONNECTION=pgsql\n"
            "DB_HOST=localhost\n"
            "DB_PORT=5432\n"
            "DB_USERNAME=user\n"
            "DB_PASSWORD=pass\n"
            "DB_DATABASE=testdb\n"
        )
        fk_file = tmp_path / "bad.json"
        fk_file.write_text("{bad json")

        result = main([
            "--env", str(env_file),
            "--fk-map", str(fk_file),
        ])
        assert result == 1

    @patch("db_schema_export.cli.create_connector")
    def test_database_connection_failure_returns_1(
        self, mock_create_connector, tmp_path
    ):
        """Should return exit code 1 when all databases fail to connect."""
        env_file = tmp_path / ".env"
        env_file.write_text(
            "DB_CONNECTION=pgsql\n"
            "DB_HOST=localhost\n"
            "DB_PORT=5432\n"
            "DB_USERNAME=user\n"
            "DB_PASSWORD=pass\n"
            "DB_DATABASE=testdb\n"
        )

        mock_connector = MagicMock()
        mock_connector.connect.side_effect = DatabaseConnectionError(
            host="localhost", port=5432, database="testdb", reason="Connection refused"
        )
        mock_create_connector.return_value = mock_connector

        result = main(["--env", str(env_file), "--output", str(tmp_path)])
        assert result == 1

    @patch("db_schema_export.cli.create_connector")
    def test_successful_single_database(self, mock_create_connector, tmp_path):
        """Should return exit code 0 when database processes successfully."""
        env_file = tmp_path / ".env"
        env_file.write_text(
            "DB_CONNECTION=pgsql\n"
            "DB_HOST=localhost\n"
            "DB_PORT=5432\n"
            "DB_USERNAME=user\n"
            "DB_PASSWORD=pass\n"
            "DB_DATABASE=testdb\n"
        )

        # Mock connector
        mock_connector = MagicMock()
        mock_create_connector.return_value = mock_connector

        # Mock execute_query to return appropriate data for each query
        mock_connector.execute_query.return_value = []

        # Patch MetadataCollector
        with patch("db_schema_export.cli.MetadataCollector") as mock_collector_cls:
            mock_collector = MagicMock()
            mock_collector_cls.return_value = mock_collector
            mock_collector.get_schemas.return_value = ["public"]

            # Mock collect_all to return minimal metadata
            from db_schema_export.models import SchemaMetadata

            mock_collector.collect_all.return_value = SchemaMetadata(
                database_name="testdb",
                schemas=["public"],
                tables=[],
                foreign_keys=[],
                views=[],
                functions=[],
                triggers=[],
            )

            # Patch MarkdownGenerator
            with patch("db_schema_export.cli.MarkdownGenerator") as mock_gen_cls:
                mock_gen = MagicMock()
                mock_gen_cls.return_value = mock_gen
                output_file = str(tmp_path / "testdb_schema.md")
                mock_gen.generate.return_value = output_file

                result = main([
                    "--env", str(env_file),
                    "--output", str(tmp_path),
                ])
                assert result == 0

    @patch("db_schema_export.cli.create_connector")
    def test_partial_success_returns_2(self, mock_create_connector, tmp_path):
        """Should return exit code 2 when some databases fail."""
        env_file = tmp_path / ".env"
        env_file.write_text(
            "DB_CONNECTION=pgsql\n"
            "DB_HOST=localhost\n"
            "DB_PORT=5432\n"
            "DB_USERNAME=user\n"
            "DB_PASSWORD=pass\n"
            "DB_DATABASES=db1,db2\n"
        )

        call_count = [0]

        def side_effect_connect():
            call_count[0] += 1
            if call_count[0] == 1:
                raise DatabaseConnectionError(
                    host="localhost", port=5432, database="db1",
                    reason="Connection refused",
                )

        # First connector fails, second succeeds
        mock_connector_fail = MagicMock()
        mock_connector_fail.connect.side_effect = DatabaseConnectionError(
            host="localhost", port=5432, database="db1",
            reason="Connection refused",
        )

        mock_connector_ok = MagicMock()

        mock_create_connector.side_effect = [mock_connector_fail, mock_connector_ok]

        with patch("db_schema_export.cli.MetadataCollector") as mock_collector_cls:
            mock_collector = MagicMock()
            mock_collector_cls.return_value = mock_collector
            mock_collector.get_schemas.return_value = ["public"]

            from db_schema_export.models import SchemaMetadata

            mock_collector.collect_all.return_value = SchemaMetadata(
                database_name="db2",
                schemas=["public"],
                tables=[],
                foreign_keys=[],
                views=[],
                functions=[],
                triggers=[],
            )

            with patch("db_schema_export.cli.MarkdownGenerator") as mock_gen_cls:
                mock_gen = MagicMock()
                mock_gen_cls.return_value = mock_gen
                mock_gen.generate.return_value = str(tmp_path / "db2_schema.md")

                result = main([
                    "--env", str(env_file),
                    "--output", str(tmp_path),
                ])
                assert result == 2

    @patch("db_schema_export.cli.create_connector")
    def test_no_infer_fk_skips_inference(self, mock_create_connector, tmp_path):
        """--no-infer-fk should skip FK inference engine."""
        env_file = tmp_path / ".env"
        env_file.write_text(
            "DB_CONNECTION=pgsql\n"
            "DB_HOST=localhost\n"
            "DB_PORT=5432\n"
            "DB_USERNAME=user\n"
            "DB_PASSWORD=pass\n"
            "DB_DATABASE=testdb\n"
        )

        mock_connector = MagicMock()
        mock_create_connector.return_value = mock_connector

        with patch("db_schema_export.cli.MetadataCollector") as mock_collector_cls:
            mock_collector = MagicMock()
            mock_collector_cls.return_value = mock_collector
            mock_collector.get_schemas.return_value = ["public"]

            from db_schema_export.models import SchemaMetadata

            mock_collector.collect_all.return_value = SchemaMetadata(
                database_name="testdb",
                schemas=["public"],
                tables=[],
                foreign_keys=[],
                views=[],
                functions=[],
                triggers=[],
            )

            with patch("db_schema_export.cli.FKInferenceEngine") as mock_fk_cls:
                with patch("db_schema_export.cli.MarkdownGenerator") as mock_gen_cls:
                    mock_gen = MagicMock()
                    mock_gen_cls.return_value = mock_gen
                    mock_gen.generate.return_value = str(tmp_path / "testdb_schema.md")

                    result = main([
                        "--env", str(env_file),
                        "--output", str(tmp_path),
                        "--no-infer-fk",
                    ])
                    assert result == 0
                    # FK inference engine should NOT have been called
                    mock_fk_cls.assert_not_called()

    @patch("db_schema_export.cli.create_connector")
    def test_schema_validation_warns_for_missing(
        self, mock_create_connector, tmp_path, capsys
    ):
        """Should warn for missing schemas and continue with valid ones."""
        env_file = tmp_path / ".env"
        env_file.write_text(
            "DB_CONNECTION=pgsql\n"
            "DB_HOST=localhost\n"
            "DB_PORT=5432\n"
            "DB_USERNAME=user\n"
            "DB_PASSWORD=pass\n"
            "DB_DATABASE=testdb\n"
        )

        mock_connector = MagicMock()
        mock_create_connector.return_value = mock_connector

        with patch("db_schema_export.cli.MetadataCollector") as mock_collector_cls:
            mock_collector = MagicMock()
            mock_collector_cls.return_value = mock_collector
            # Only "public" exists, "nonexistent" does not
            mock_collector.get_schemas.return_value = ["public"]

            from db_schema_export.models import SchemaMetadata

            mock_collector.collect_all.return_value = SchemaMetadata(
                database_name="testdb",
                schemas=["public"],
                tables=[],
                foreign_keys=[],
                views=[],
                functions=[],
                triggers=[],
            )

            with patch("db_schema_export.cli.MarkdownGenerator") as mock_gen_cls:
                mock_gen = MagicMock()
                mock_gen_cls.return_value = mock_gen
                mock_gen.generate.return_value = str(tmp_path / "testdb_schema.md")

                result = main([
                    "--env", str(env_file),
                    "--output", str(tmp_path),
                    "--schema", "public,nonexistent",
                ])
                assert result == 0

                # Check warning was printed
                captured = capsys.readouterr()
                assert "nonexistent" in captured.err

    @patch("db_schema_export.cli.create_connector")
    def test_all_schemas_invalid_skips_database(
        self, mock_create_connector, tmp_path
    ):
        """Should skip database when all specified schemas are invalid."""
        env_file = tmp_path / ".env"
        env_file.write_text(
            "DB_CONNECTION=pgsql\n"
            "DB_HOST=localhost\n"
            "DB_PORT=5432\n"
            "DB_USERNAME=user\n"
            "DB_PASSWORD=pass\n"
            "DB_DATABASE=testdb\n"
        )

        mock_connector = MagicMock()
        mock_create_connector.return_value = mock_connector

        with patch("db_schema_export.cli.MetadataCollector") as mock_collector_cls:
            mock_collector = MagicMock()
            mock_collector_cls.return_value = mock_collector
            mock_collector.get_schemas.return_value = ["public"]

            result = main([
                "--env", str(env_file),
                "--output", str(tmp_path),
                "--schema", "nonexistent1,nonexistent2",
            ])
            # All databases failed (only one db, all schemas invalid)
            assert result == 1
