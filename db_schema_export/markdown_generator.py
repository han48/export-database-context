"""Markdown Generator for Database Schema Export Tool.

This module generates comprehensive Markdown output files from collected
database metadata. It produces sections for ERD diagrams (Mermaid), table
details, views, functions, and triggers.

The generator supports:
- Table of contents with anchor links
- Mermaid erDiagram with confirmed and inferred relationships
- Detailed table column information
- View definitions with SQL code blocks
- Function/procedure summary tables
- Trigger information grouped by table
- Multi-schema prefix support
- Section filtering via --sections argument
"""

from __future__ import annotations

import os
from typing import Union

from db_schema_export.exceptions import OutputWriteError
from db_schema_export.models import (
    ColumnMetadata,
    ForeignKeyMetadata,
    FunctionMetadata,
    InferredFK,
    OperatorMetadata,
    SchemaMetadata,
    SequenceMetadata,
    TableMetadata,
    TriggerMetadata,
    TypeMetadata,
    ViewMetadata,
)

# Valid section names
VALID_SECTIONS = ["erd", "tables", "views", "functions", "triggers", "types", "sequences", "operators"]

# Section display names for headings and TOC
SECTION_HEADINGS: dict[str, str] = {
    "erd": "ERD Diagram",
    "tables": "Tables",
    "views": "Views",
    "functions": "Functions/Procedures",
    "triggers": "Triggers",
    "types": "Types",
    "sequences": "Sequences",
    "operators": "Operators",
}


class MarkdownGenerator:
    """Generates Markdown output file from collected metadata.

    Attributes:
        metadata: The complete schema metadata for a database.
        relationships: Combined list of confirmed and inferred FK relationships.
        sections: List of section names to include in the output.
        multi_schema: Whether multiple schemas are being exported.
    """

    def __init__(
        self,
        metadata: SchemaMetadata,
        relationships: list[Union[ForeignKeyMetadata, InferredFK]],
        sections: list[str],
        multi_schema: bool = False,
    ) -> None:
        """Initialize the Markdown Generator.

        Args:
            metadata: SchemaMetadata containing all database objects.
            relationships: Combined list of ForeignKeyMetadata (confirmed)
                and InferredFK (inferred) objects.
            sections: List of section names to include (e.g., ["erd", "tables"]).
            multi_schema: If True, prefix object names with schema name.
        """
        self.metadata = metadata
        self.relationships = relationships
        self.sections = [s for s in sections if s in VALID_SECTIONS]
        self.multi_schema = multi_schema

    def generate(self, output_path: str) -> str:
        """Generate complete Markdown file and write to disk.

        Constructs the full Markdown document with title, TOC, and all
        requested sections, then writes it to the specified output path.

        Args:
            output_path: Directory path where the output file will be written.

        Returns:
            The full file path of the generated Markdown file.

        Raises:
            OutputWriteError: If the file cannot be written.
        """
        filename = f"{self.metadata.database_name}_schema.md"
        filepath = os.path.join(output_path, filename)

        # Build the document
        parts: list[str] = []

        # Title
        parts.append(f"# {self.metadata.database_name} - Database Schema\n")

        # Table of contents
        parts.append(self._generate_toc())

        # Generate each requested section
        section_generators = {
            "erd": self._generate_erd_section,
            "tables": self._generate_tables_section,
            "views": self._generate_views_section,
            "functions": self._generate_functions_section,
            "triggers": self._generate_triggers_section,
            "types": self._generate_types_section,
            "sequences": self._generate_sequences_section,
            "operators": self._generate_operators_section,
        }

        for section in self.sections:
            if section in section_generators:
                parts.append(section_generators[section]())

        content = "\n".join(parts)

        # Write to file
        try:
            os.makedirs(output_path, exist_ok=True)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
        except OSError as e:
            raise OutputWriteError(filepath, str(e))

        # Export ERD as high-resolution PNG image if ERD section is included
        if "erd" in self.sections and self.metadata.tables:
            self._export_erd_image(output_path)

        return filepath

    def _export_erd_image(self, output_path: str) -> str | None:
        """Export the ERD Mermaid diagram as a high-resolution PNG image.

        Uses @mermaid-js/mermaid-cli (mmdc) to render the ERD diagram.
        Requires mmdc to be installed (npx @mermaid-js/mermaid-cli or global install).

        The image is exported at high DPI (scale factor 4) to ensure text
        remains readable when zoomed in on large diagrams.

        Args:
            output_path: Directory where the image will be saved.

        Returns:
            Path to the generated PNG file, or None if export failed.
        """
        import shutil
        import subprocess
        import tempfile

        # Check if mmdc is available
        mmdc_cmd = shutil.which("mmdc")
        if mmdc_cmd is None:
            # Try npx as fallback
            npx_cmd = shutil.which("npx")
            if npx_cmd is None:
                print(
                    "[WARNING] mmdc (mermaid-cli) not found. "
                    "Skipping ERD image export. "
                    "Install with: npm install -g @mermaid-js/mermaid-cli",
                    file=__import__("sys").stderr,
                )
                return None
            mmdc_cmd = npx_cmd
            mmdc_args = [mmdc_cmd, "-p", "@mermaid-js/mermaid-cli", "mmdc"]
        else:
            mmdc_args = [mmdc_cmd]

        # Generate the Mermaid ERD content (without the markdown code fence)
        erd_content = self._generate_erd_mermaid_content()
        if not erd_content:
            return None

        # Write Mermaid content to a temp file
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".mmd", delete=False, encoding="utf-8"
            ) as tmp_file:
                tmp_file.write(erd_content)
                tmp_mmd_path = tmp_file.name

            # Output PNG path
            png_filename = f"{self.metadata.database_name}_erd.png"
            png_path = os.path.join(output_path, png_filename)

            # Run mmdc with high resolution settings
            # -s 4 = scale factor 4x for high DPI
            # -w 4096 = wide viewport to accommodate many tables
            # -H 4096 = tall viewport
            # -b white = white background
            cmd = mmdc_args + [
                "-i", tmp_mmd_path,
                "-o", png_path,
                "-s", "4",
                "-w", "4096",
                "-H", "4096",
                "-b", "white",
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
            )

            if result.returncode == 0:
                print(f"  ✓ ERD image exported: {png_path}")
                return png_path
            else:
                print(
                    f"[WARNING] ERD image export failed: {result.stderr.strip()}",
                    file=__import__("sys").stderr,
                )
                return None

        except FileNotFoundError:
            print(
                "[WARNING] mmdc command not found. Skipping ERD image export.",
                file=__import__("sys").stderr,
            )
            return None
        except subprocess.TimeoutExpired:
            print(
                "[WARNING] ERD image export timed out (>120s). Skipping.",
                file=__import__("sys").stderr,
            )
            return None
        except Exception as e:
            print(
                f"[WARNING] ERD image export failed: {e}",
                file=__import__("sys").stderr,
            )
            return None
        finally:
            # Clean up temp file
            try:
                os.unlink(tmp_mmd_path)
            except (OSError, UnboundLocalError):
                pass

    def _generate_erd_mermaid_content(self) -> str:
        """Generate raw Mermaid ERD content (without markdown code fences).

        Returns:
            Mermaid erDiagram content string.
        """
        lines: list[str] = []
        lines.append("erDiagram")

        # Relationships
        for rel in self.relationships:
            source_table = self._get_table_display_name_erd(
                self._get_rel_source_schema(rel),
                self._get_rel_source_table(rel),
            )
            target_table = self._get_table_display_name_erd(
                self._get_rel_target_schema(rel),
                self._get_rel_target_table(rel),
            )
            is_inferred = self._is_inferred_relationship(rel)
            cardinality = self._determine_cardinality(rel)

            if is_inferred:
                rel_line = f"    {target_table} {cardinality.replace('--', '..')} {source_table} : \"{self._get_rel_label(rel)}\""
            else:
                rel_line = f"    {target_table} {cardinality} {source_table} : \"{self._get_rel_label(rel)}\""
            lines.append(rel_line)

        # Entities
        for table in self.metadata.tables:
            table_name = self._get_table_display_name_erd(table.schema, table.name)
            lines.append(f"    {table_name} {{")
            for col in table.columns:
                data_type = self._sanitize_erd_type(col.data_type)
                if col.is_primary_key:
                    marker = " PK"
                elif col.is_foreign_key:
                    marker = " FK"
                else:
                    marker = ""
                lines.append(f"        {data_type} {col.name}{marker}")
            lines.append("    }")

        return "\n".join(lines)

    def _generate_toc(self) -> str:
        """Generate table of contents with anchor links.

        Creates a TOC section with links to each included section heading.

        Returns:
            Markdown string containing the table of contents.
        """
        lines: list[str] = []
        lines.append("## Table of Contents\n")

        for section in self.sections:
            heading = SECTION_HEADINGS.get(section, section.title())
            # Generate anchor link (lowercase, spaces to hyphens, remove special chars)
            anchor = heading.lower().replace(" ", "-").replace("/", "")
            lines.append(f"- [{heading}](#{anchor})")

        lines.append("")
        return "\n".join(lines)

    def _generate_erd_section(self) -> str:
        """Generate Mermaid erDiagram section.

        Renders all tables as entities with their columns and data types,
        and draws relationships between them using Mermaid notation.
        Confirmed FKs use solid lines (--), inferred FKs use dashed lines (..).

        Returns:
            Markdown string containing the ERD section.
        """
        lines: list[str] = []
        lines.append("## ERD Diagram\n")

        # Legend
        lines.append("> **Legend:**")
        lines.append("> - Solid lines (`──`) represent confirmed foreign key constraints from the database")
        lines.append("> - Dashed lines (`╌╌`) represent inferred relationships based on naming conventions\n")

        # Start Mermaid block
        lines.append("```mermaid")
        lines.append("erDiagram")

        # Collect relationships
        rendered_relationships: list[str] = []
        tables_with_relationships: set[str] = set()

        for rel in self.relationships:
            source_table = self._get_table_display_name_erd(
                self._get_rel_source_schema(rel),
                self._get_rel_source_table(rel),
            )
            target_table = self._get_table_display_name_erd(
                self._get_rel_target_schema(rel),
                self._get_rel_target_table(rel),
            )

            # Determine if confirmed or inferred
            is_inferred = self._is_inferred_relationship(rel)

            # Determine cardinality
            cardinality = self._determine_cardinality(rel)

            # Build relationship line
            if is_inferred:
                # Dashed lines for inferred
                rel_line = f"    {target_table} {cardinality.replace('--', '..')} {source_table} : \"{self._get_rel_label(rel)}\""
            else:
                # Solid lines for confirmed
                rel_line = f"    {target_table} {cardinality} {source_table} : \"{self._get_rel_label(rel)}\""

            rendered_relationships.append(rel_line)
            tables_with_relationships.add(source_table)
            tables_with_relationships.add(target_table)

        # Render relationships
        for rel_line in rendered_relationships:
            lines.append(rel_line)

        # Render all tables as entities
        for table in self.metadata.tables:
            table_name = self._get_table_display_name_erd(table.schema, table.name)
            lines.append(f"    {table_name} {{")
            for col in table.columns:
                # Sanitize data type for Mermaid erDiagram
                # Mermaid only allows alphanumeric and underscores in type names
                data_type = self._sanitize_erd_type(col.data_type)
                # Mermaid only supports one key marker per attribute
                if col.is_primary_key:
                    marker = " PK"
                elif col.is_foreign_key:
                    marker = " FK"
                else:
                    marker = ""
                lines.append(f"        {data_type} {col.name}{marker}")
            lines.append("    }")

        lines.append("```\n")
        return "\n".join(lines)

    def _generate_tables_section(self) -> str:
        """Generate detailed tables section.

        Creates a subsection for each table with a Markdown table showing
        column details including name, data type, key status, nullability,
        default value, and comment.

        Returns:
            Markdown string containing the tables section.
        """
        lines: list[str] = []
        lines.append("## Tables\n")

        for table in self.metadata.tables:
            # Table heading with optional schema prefix
            table_display = self._get_table_display_name(table.schema, table.name)
            lines.append(f"### {table_display}\n")

            # Table comment
            if table.comment:
                lines.append(f"_{table.comment}_\n")

            # Check for empty columns
            if not table.columns:
                lines.append("_No columns found_\n")
                continue

            # Markdown table header
            lines.append("| Column Name | Data Type | Key | Not Null | Default Value | Comment |")
            lines.append("|---|---|---|---|---|---|")

            # Render each column
            for col in table.columns:
                key = self._get_key_display(col)
                not_null = "✓" if not col.is_nullable else ""
                default = col.default_value if col.default_value else ""
                comment = col.comment if col.comment else ""
                data_type = col.data_type

                lines.append(
                    f"| {col.name} | {data_type} | {key} | {not_null} | {default} | {comment} |"
                )

            lines.append("")

        return "\n".join(lines)

    def _generate_views_section(self) -> str:
        """Generate views section with SQL definitions.

        Creates a subsection for each view showing its name, schema,
        and SQL definition in a code block.

        Returns:
            Markdown string containing the views section.
        """
        lines: list[str] = []
        lines.append("## Views\n")

        if not self.metadata.views:
            lines.append("_No views found_\n")
            return "\n".join(lines)

        for view in self.metadata.views:
            view_display = self._get_table_display_name(view.schema, view.name)
            lines.append(f"### {view_display}\n")
            lines.append(f"**Schema:** {view.schema}\n")
            lines.append("```sql")
            lines.append(view.definition)
            lines.append("```\n")

        return "\n".join(lines)

    def _generate_functions_section(self) -> str:
        """Generate functions/procedures summary table.

        Creates a single Markdown table listing all functions with their
        schema, name, arguments, return type, language, and type.

        Returns:
            Markdown string containing the functions section.
        """
        lines: list[str] = []
        lines.append("## Functions/Procedures\n")

        if not self.metadata.functions:
            lines.append("_No functions found_\n")
            return "\n".join(lines)

        # Summary table
        lines.append("| Schema | Function Name | Arguments | Return Type | Language | Type |")
        lines.append("|---|---|---|---|---|---|")

        for func in self.metadata.functions:
            lines.append(
                f"| {func.schema} | {func.name} | {func.arguments} | "
                f"{func.return_type} | {func.language} | {func.func_type} |"
            )

        lines.append("")
        return "\n".join(lines)

    def _generate_triggers_section(self) -> str:
        """Generate triggers section grouped by table.

        Creates a Markdown table for triggers, grouped by the table they
        are attached to, showing trigger name, table, timing, event, and
        function called.

        Returns:
            Markdown string containing the triggers section.
        """
        lines: list[str] = []
        lines.append("## Triggers\n")

        if not self.metadata.triggers:
            lines.append("_No triggers found_\n")
            return "\n".join(lines)

        # Group triggers by table
        triggers_by_table: dict[str, list[TriggerMetadata]] = {}
        for trigger in self.metadata.triggers:
            table_key = self._get_table_display_name(trigger.schema, trigger.table_name)
            if table_key not in triggers_by_table:
                triggers_by_table[table_key] = []
            triggers_by_table[table_key].append(trigger)

        # Render each group
        for table_name, triggers in triggers_by_table.items():
            lines.append(f"### {table_name}\n")
            lines.append("| Trigger Name | Table | Timing | Event | Function Called |")
            lines.append("|---|---|---|---|---|")

            for trigger in triggers:
                lines.append(
                    f"| {trigger.name} | {trigger.table_name} | "
                    f"{trigger.timing} | {trigger.event} | {trigger.function_name} |"
                )

            lines.append("")

        return "\n".join(lines)

    def _generate_types_section(self) -> str:
        """Generate types section.

        Creates a Markdown table listing all custom types with their
        schema, name, type category, and definition.

        Returns:
            Markdown string containing the types section.
        """
        lines: list[str] = []
        lines.append("## Types\n")

        if not self.metadata.types:
            lines.append("_No custom types found_\n")
            return "\n".join(lines)

        lines.append("| Schema | Type Name | Category | Definition |")
        lines.append("|---|---|---|---|")

        for t in self.metadata.types:
            definition = t.definition if t.definition else ""
            # Truncate long definitions
            if len(definition) > 100:
                definition = definition[:100] + "..."
            lines.append(f"| {t.schema} | {t.name} | {t.type_type} | {definition} |")

        lines.append("")
        return "\n".join(lines)

    def _generate_sequences_section(self) -> str:
        """Generate sequences section.

        Creates a Markdown table listing all sequences with their
        properties.

        Returns:
            Markdown string containing the sequences section.
        """
        lines: list[str] = []
        lines.append("## Sequences\n")

        if not self.metadata.sequences:
            lines.append("_No sequences found_\n")
            return "\n".join(lines)

        lines.append("| Schema | Sequence Name | Data Type | Start | Increment | Owned By |")
        lines.append("|---|---|---|---|---|---|")

        for seq in self.metadata.sequences:
            owned_by = seq.owned_by if seq.owned_by else ""
            start = seq.start_value if seq.start_value else ""
            increment = seq.increment if seq.increment else ""
            lines.append(
                f"| {seq.schema} | {seq.name} | {seq.data_type} | "
                f"{start} | {increment} | {owned_by} |"
            )

        lines.append("")
        return "\n".join(lines)

    def _generate_operators_section(self) -> str:
        """Generate operators section.

        Creates a Markdown table listing all custom operators.

        Returns:
            Markdown string containing the operators section.
        """
        lines: list[str] = []
        lines.append("## Operators\n")

        if not self.metadata.operators:
            lines.append("_No custom operators found_\n")
            return "\n".join(lines)

        lines.append("| Schema | Operator | Left Type | Right Type | Result Type | Function |")
        lines.append("|---|---|---|---|---|---|")

        for op in self.metadata.operators:
            left = op.left_type if op.left_type else "-"
            right = op.right_type if op.right_type else "-"
            lines.append(
                f"| {op.schema} | `{op.name}` | {left} | {right} | "
                f"{op.result_type} | {op.function_name} |"
            )

        lines.append("")
        return "\n".join(lines)

    # --- Helper methods ---

    @staticmethod
    def _sanitize_erd_type(data_type: str) -> str:
        """Sanitize a data type string for Mermaid erDiagram compatibility.

        Mermaid erDiagram only allows alphanumeric characters and underscores
        in type names. This method removes or replaces special characters
        like parentheses, commas, brackets, etc.

        Examples:
            'numeric(3,2)' → 'numeric_3_2'
            'character varying' → 'character_varying'
            'timestamp without time zone' → 'timestamp_without_time_zone'
            'integer[]' → 'integer_array'

        Args:
            data_type: Raw data type string from PostgreSQL.

        Returns:
            Sanitized string safe for Mermaid erDiagram.
        """
        # Replace array brackets
        result = data_type.replace("[]", "_array")
        # Replace parentheses content: numeric(3,2) → numeric_3_2
        result = result.replace("(", "_").replace(")", "").replace(",", "_")
        # Replace spaces with underscores
        result = result.replace(" ", "_")
        # Remove any remaining special characters
        result = "".join(c if c.isalnum() or c == "_" else "_" for c in result)
        # Collapse multiple underscores
        while "__" in result:
            result = result.replace("__", "_")
        # Strip trailing underscores
        result = result.strip("_")
        return result

    def _get_table_display_name(self, schema: str, name: str) -> str:
        """Get display name for a table, with optional schema prefix.

        Args:
            schema: The schema name.
            name: The table/view name.

        Returns:
            Display name with schema prefix if multi_schema is True.
        """
        if self.multi_schema:
            return f"{schema}.{name}"
        return name

    def _get_table_display_name_erd(self, schema: str, name: str) -> str:
        """Get display name for ERD entities (no dots allowed in Mermaid).

        Mermaid entity names cannot contain dots, so we use underscores
        as separators when multi_schema is True.

        Args:
            schema: The schema name.
            name: The table name.

        Returns:
            ERD-safe display name.
        """
        if self.multi_schema:
            return f"{schema}__{name}"
        return name

    def _get_key_display(self, col: ColumnMetadata) -> str:
        """Get the key display string for a column.

        Args:
            col: The column metadata.

        Returns:
            'PK', 'FK', 'PK, FK', or empty string.
        """
        parts: list[str] = []
        if col.is_primary_key:
            parts.append("PK")
        if col.is_foreign_key:
            parts.append("FK")
        return ", ".join(parts)

    def _is_inferred_relationship(
        self, rel: Union[ForeignKeyMetadata, InferredFK]
    ) -> bool:
        """Determine if a relationship is inferred or confirmed.

        Args:
            rel: A relationship object (ForeignKeyMetadata or InferredFK).

        Returns:
            True if the relationship is inferred, False if confirmed.
        """
        if isinstance(rel, InferredFK):
            return True
        if isinstance(rel, ForeignKeyMetadata):
            return rel.status == "inferred"
        return False

    def _get_rel_source_schema(self, rel: Union[ForeignKeyMetadata, InferredFK]) -> str:
        """Get source schema from a relationship object."""
        return rel.source_schema

    def _get_rel_source_table(self, rel: Union[ForeignKeyMetadata, InferredFK]) -> str:
        """Get source table from a relationship object."""
        return rel.source_table

    def _get_rel_target_schema(self, rel: Union[ForeignKeyMetadata, InferredFK]) -> str:
        """Get target schema from a relationship object."""
        return rel.target_schema

    def _get_rel_target_table(self, rel: Union[ForeignKeyMetadata, InferredFK]) -> str:
        """Get target table from a relationship object."""
        return rel.target_table

    def _get_rel_label(self, rel: Union[ForeignKeyMetadata, InferredFK]) -> str:
        """Get a label for the relationship line in the ERD.

        Args:
            rel: A relationship object.

        Returns:
            A descriptive label string.
        """
        if isinstance(rel, InferredFK):
            return "inferred"
        if isinstance(rel, ForeignKeyMetadata) and rel.status == "inferred":
            return "inferred"
        # For confirmed FKs, use the column name as label
        return rel.source_column

    def _determine_cardinality(
        self, rel: Union[ForeignKeyMetadata, InferredFK]
    ) -> str:
        """Determine the Mermaid cardinality notation for a relationship.

        Logic:
        - Look up the source column in the source table
        - If the column is nullable: use zero-or-many (o{)
        - If the column is not nullable: use one-to-many (|{)

        The left side (target/referenced table) is always ||.

        Args:
            rel: A relationship object.

        Returns:
            Mermaid cardinality string (e.g., '||--o{', '||--|{').
        """
        source_table_name = self._get_rel_source_table(rel)
        source_column_name = rel.source_column

        # Find the source column to check nullable status
        is_nullable = True  # Default to nullable (zero-or-many)
        for table in self.metadata.tables:
            if table.name == source_table_name and table.schema == self._get_rel_source_schema(rel):
                for col in table.columns:
                    if col.name == source_column_name:
                        is_nullable = col.is_nullable
                        break
                break

        # Determine cardinality
        if is_nullable:
            return "||--o{"
        else:
            return "||--|{"
