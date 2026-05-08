"""CLI entry point for Database Schema Export Tool.

This module provides the command-line interface and orchestration logic
for the database schema export tool. It handles argument parsing, validation,
and coordinates the pipeline: env parsing → DB connection → metadata collection
→ FK inference → markdown generation.

Exit codes:
    0: Success (all databases processed, may have warnings)
    1: Fatal error (config error, file error, all databases failed)
    2: Partial success (some databases/queries failed but some output generated)

Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7, 10.8, 10.9, 10.10,
              12.2, 12.3, 12.4, 12.5, 12.6, 13.10, 13.11, 13.12
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Union

from db_schema_export.db_connector import create_connector
from db_schema_export.env_parser import parse_env
from db_schema_export.exceptions import (
    AllSchemasInvalidError,
    DatabaseConnectionError,
    FKMapFileNotFoundError,
    FKMapParseError,
    SchemaExportError,
    SchemaNotFoundWarning,
)
from db_schema_export.fk_inference_engine import FKInferenceEngine
from db_schema_export.markdown_generator import VALID_SECTIONS, MarkdownGenerator
from db_schema_export.metadata_collector import MetadataCollector
from db_schema_export.models import ForeignKeyMetadata, InferredFK


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        argv: List of argument strings. If None, uses sys.argv[1:].

    Returns:
        Parsed arguments as argparse.Namespace with attributes:
            output, env, schema, sections, no_infer_fk, fk_map.
    """
    parser = argparse.ArgumentParser(
        prog="db_schema_export",
        description="Export PostgreSQL database schema to Markdown files.",
    )

    parser.add_argument(
        "--output",
        type=str,
        default=".",
        help="Output directory for generated Markdown files (default: current directory)",
    )

    parser.add_argument(
        "--env",
        type=str,
        default=".env",
        help="Path to .env file containing database configuration (default: .env)",
    )

    parser.add_argument(
        "--schema",
        type=str,
        default=None,
        help="Comma-separated list of schema names to export (default: all non-system schemas)",
    )

    parser.add_argument(
        "--sections",
        type=str,
        default=None,
        help=(
            "Comma-separated list of sections to include in output. "
            f"Valid values: {', '.join(VALID_SECTIONS)} (default: all sections)"
        ),
    )

    parser.add_argument(
        "--no-infer-fk",
        action="store_true",
        default=False,
        help="Disable FK inference engine (only use explicit FK constraints)",
    )

    parser.add_argument(
        "--fk-map",
        type=str,
        default=None,
        help="Path to FK mapping file (JSON) for manual FK relationship definitions",
    )

    parser.add_argument(
        "--analyze",
        action="store_true",
        default=False,
        help="Run AI analysis on generated schema files using Qwen3-1.7B (requires transformers, torch)",
    )

    return parser.parse_args(argv)


def _validate_fk_map(fk_map_path: str) -> dict[str, str]:
    """Validate and parse the FK mapping file.

    Args:
        fk_map_path: Path to the FK mapping JSON file.

    Returns:
        Parsed dictionary from the JSON file.

    Raises:
        FKMapFileNotFoundError: If the file does not exist.
        FKMapParseError: If the file contains invalid JSON.
    """
    if not os.path.isfile(fk_map_path):
        raise FKMapFileNotFoundError(fk_map_path)

    try:
        with open(fk_map_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise FKMapParseError(
            path=fk_map_path,
            parse_error=str(e),
            line_number=e.lineno,
        ) from e

    if not isinstance(data, dict):
        raise FKMapParseError(
            path=fk_map_path,
            parse_error="Expected a JSON object (dictionary) at top level",
        )

    return data


def _parse_sections(sections_arg: str | None) -> list[str]:
    """Parse and validate the --sections argument.

    Args:
        sections_arg: Comma-separated sections string, or None for all sections.

    Returns:
        List of valid section names.
    """
    if sections_arg is None:
        return list(VALID_SECTIONS)

    sections = [s.strip().lower() for s in sections_arg.split(",") if s.strip()]
    valid = [s for s in sections if s in VALID_SECTIONS]
    invalid = [s for s in sections if s not in VALID_SECTIONS]

    if invalid:
        print(
            f"[WARNING] Invalid section names ignored: {', '.join(invalid)}. "
            f"Valid sections: {', '.join(VALID_SECTIONS)}",
            file=sys.stderr,
        )

    if not valid:
        return list(VALID_SECTIONS)

    return valid


def _parse_schemas(schema_arg: str | None) -> list[str] | None:
    """Parse the --schema argument.

    Args:
        schema_arg: Comma-separated schema string, or None for auto-detect.

    Returns:
        List of schema names, or None to auto-detect all non-system schemas.
    """
    if schema_arg is None:
        return None

    schemas = [s.strip() for s in schema_arg.split(",") if s.strip()]
    return schemas if schemas else None


def main(argv: list[str] | None = None) -> int:
    """Main orchestration function.

    Coordinates the full pipeline: parse args → parse .env → validate FK map
    → for each database: connect → collect metadata → infer FK → generate markdown.

    Implements graceful degradation:
    - If one database fails → log error, continue with others
    - If a schema doesn't exist → warning, continue with valid schemas
    - If a metadata query fails → MetadataCollector handles internally

    Args:
        argv: List of argument strings. If None, uses sys.argv[1:].

    Returns:
        Exit code: 0=success, 1=fatal error, 2=partial success.
    """
    # 1. Parse CLI arguments
    args = parse_args(argv)

    # 2. Parse .env file
    try:
        config = parse_env(args.env)
    except SchemaExportError as e:
        print(e.format_message(), file=sys.stderr)
        return 1

    # 3. Validate --fk-map file if provided
    fk_mapping: dict[str, str] | None = None
    if args.fk_map:
        try:
            fk_mapping = _validate_fk_map(args.fk_map)
        except FKMapFileNotFoundError as e:
            # File not found is a warning - continue without FK mapping
            print(
                f"[WARNING] FK mapping file not found: {args.fk_map}\n"
                f"  → Continuing without FK mapping overrides",
                file=sys.stderr,
            )
        except FKMapParseError as e:
            # Invalid JSON is a fatal error
            print(e.format_message(), file=sys.stderr)
            return 1

    # Parse sections and schemas
    sections = _parse_sections(args.sections)
    requested_schemas = _parse_schemas(args.schema)

    # 4. Process each database
    generated_files: list[str] = []
    failed_databases: list[str] = []

    for database in config.databases:
        try:
            result = _process_database(
                config=config,
                database=database,
                output_dir=args.output,
                sections=sections,
                requested_schemas=requested_schemas,
                no_infer_fk=args.no_infer_fk,
                fk_mapping=fk_mapping,
            )
            if result is not None:
                generated_files.append(result)
            else:
                failed_databases.append(database)
        except Exception as e:
            print(
                f"[ERROR] Unexpected error processing database '{database}': {e}",
                file=sys.stderr,
            )
            failed_databases.append(database)

    # 5. Print summary
    _print_summary(generated_files, failed_databases)

    # 6. Run AI analysis if requested
    if args.analyze and generated_files:
        _run_ai_analysis(generated_files)

    # 7. Determine exit code
    if not generated_files and failed_databases:
        return 1
    elif generated_files and failed_databases:
        return 2
    else:
        return 0


def _process_database(
    config,
    database: str,
    output_dir: str,
    sections: list[str],
    requested_schemas: list[str] | None,
    no_infer_fk: bool,
    fk_mapping: dict[str, str] | None,
) -> str | None:
    """Process a single database through the full pipeline.

    Args:
        config: DbConfig with connection parameters.
        database: Name of the database to process.
        output_dir: Output directory for the generated file.
        sections: List of sections to include.
        requested_schemas: List of schemas to export, or None for all.
        no_infer_fk: If True, disable FK inference.
        fk_mapping: Optional FK mapping dictionary.

    Returns:
        Path to the generated file, or None if processing failed.
    """
    # a. Create connector
    try:
        connector = create_connector(config, database)
    except (NotImplementedError, ValueError) as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return None

    # b. Connect to database
    try:
        connector.connect()
    except DatabaseConnectionError as e:
        print(e.format_message(), file=sys.stderr)
        return None

    try:
        # c. Create MetadataCollector
        collector = MetadataCollector(connector)

        # d. Get available schemas (or use --schema filter)
        if requested_schemas is not None:
            # Validate schemas exist
            available_schemas = collector.get_schemas()
            valid_schemas: list[str] = []
            invalid_schemas: list[str] = []

            for schema in requested_schemas:
                if schema in available_schemas:
                    valid_schemas.append(schema)
                else:
                    invalid_schemas.append(schema)

            # e. Warn for missing schemas
            for schema in invalid_schemas:
                remaining = [s for s in valid_schemas]
                warning = SchemaNotFoundWarning(
                    schema=schema,
                    database=database,
                    remaining_schemas=remaining,
                )
                print(str(warning), file=sys.stderr)

            # Error if all schemas invalid
            if not valid_schemas:
                error = AllSchemasInvalidError(
                    schemas=invalid_schemas,
                    database=database,
                )
                print(error.format_message(), file=sys.stderr)
                return None

            schemas = valid_schemas
        else:
            # Auto-detect all non-system schemas
            schemas = collector.get_schemas()
            if not schemas:
                print(
                    f"[WARNING] No non-system schemas found in database '{database}'. "
                    f"Generating empty schema file.",
                    file=sys.stderr,
                )
                schemas = []

        # Determine if multi-schema
        multi_schema = len(schemas) > 1

        # f. Collect metadata
        metadata = collector.collect_all(schemas=schemas, database_name=database)

        # g. Run FK inference (unless --no-infer-fk)
        relationships: list[Union[ForeignKeyMetadata, InferredFK]] = list(
            metadata.foreign_keys
        )

        if not no_infer_fk:
            engine = FKInferenceEngine(
                tables=metadata.tables,
                fk_mapping=fk_mapping,
            )
            inferred = engine.infer_all()
            relationships.extend(inferred)

        # h. Generate markdown
        generator = MarkdownGenerator(
            metadata=metadata,
            relationships=relationships,
            sections=sections,
            multi_schema=multi_schema,
        )
        filepath = generator.generate(output_dir)
        return filepath

    finally:
        connector.close()


def _print_summary(generated_files: list[str], failed_databases: list[str]) -> None:
    """Print execution summary to stdout.

    Args:
        generated_files: List of successfully generated file paths.
        failed_databases: List of database names that failed processing.
    """
    print("\n" + "=" * 60)
    print("Database Schema Export - Summary")
    print("=" * 60)

    total = len(generated_files) + len(failed_databases)
    print(f"\nDatabases processed: {len(generated_files)}/{total}")

    if generated_files:
        print("\nGenerated files:")
        for filepath in generated_files:
            print(f"  ✓ {filepath}")

    if failed_databases:
        print("\nFailed databases:")
        for db in failed_databases:
            print(f"  ✗ {db}")

    print()

def _run_ai_analysis(generated_files: list[str]) -> None:
    """Run AI analysis on generated schema files.

    Uses the ai_analyzer module with Qwen3-1.7B to produce
    detailed analysis of each schema file with streaming output.

    Args:
        generated_files: List of generated schema markdown file paths.
    """
    try:
        from db_schema_export.ai_analyzer import (
            analyze_schema,
            get_output_path,
            load_model,
            read_schema_file,
        )
    except ImportError as e:
        print(
            f"\n[WARNING] Cannot run AI analysis: {e}\n"
            f"  → Install with: pip install transformers torch accelerate",
            file=sys.stderr,
        )
        return

    print("\n" + "=" * 60)
    print("AI Schema Analysis (Qwen3-1.7B)")
    print("=" * 60 + "\n")

    try:
        model, tokenizer = load_model()
    except Exception as e:
        print(f"[ERROR] Failed to load AI model: {e}", file=sys.stderr)
        return

    for filepath in generated_files:
        print(f"\nAnalyzing: {filepath}")
        try:
            schema_content = read_schema_file(filepath)
            output_path = get_output_path(filepath)
            analysis = analyze_schema(model, tokenizer, schema_content, output_path)

            if analysis.strip():
                print(f"\n  ✓ Analysis saved: {output_path}")
            else:
                print(f"  ✗ Empty analysis generated for {filepath}")
        except Exception as e:
            print(f"  ✗ Analysis failed for {filepath}: {e}", file=sys.stderr)
