# DB Schema Export

> 🌐 Language: **English** | [日本語](README.ja.md) | [Tiếng Việt](README.vi.md)

Export PostgreSQL database schema to comprehensive Markdown documentation with ERD diagrams, FK inference, and optional AI-powered analysis.

## Features

- **Schema Export**: Export full database schema (tables, views, functions, triggers, types, sequences, operators) to Markdown
- **ERD Diagram**: Auto-generate Mermaid erDiagram with confirmed and inferred relationships
- **ERD Image Export**: Render ERD as high-resolution PNG using mermaid-cli
- **FK Inference Engine**: Automatically infer foreign key relationships based on naming conventions (4 confidence levels)
- **FK Mapping Override**: Manual FK relationship definitions via JSON file
- **Multi-Database Support**: Process multiple databases from a single `.env` file
- **Multi-Schema Support**: Export multiple schemas with proper prefixing
- **Section Filtering**: Choose which sections to include in output
- **AI Analysis** (optional): Analyze schema using Qwen3-1.7B with streaming output

## Installation

### Requirements

- Python >= 3.9
- PostgreSQL database

### Install from source

```bash
pip install -e .
```

### Install with AI analysis support

```bash
pip install -e ".[ai]"
```

### Install with development dependencies

```bash
pip install -e ".[dev]"
```

## Configuration

Create a `.env` file with your database connection settings:

```env
DB_CONNECTION=pgsql
DB_HOST=localhost
DB_PORT=5432
DB_USERNAME=postgres
DB_PASSWORD=your_password

# Single database
DB_DATABASE=my_database

# Or multiple databases (comma-separated)
DB_DATABASES=db_one, db_two, db_three
```

`DB_DATABASES` takes priority over `DB_DATABASE` when both are defined.

## Usage

### Basic export

```bash
db-schema-export
```

### Specify output directory and env file

```bash
db-schema-export --output ./docs --env .env.production
```

### Filter schemas

```bash
db-schema-export --schema public,salesforce
```

### Filter sections

```bash
db-schema-export --sections erd,tables,views
```

Valid sections: `erd`, `tables`, `views`, `functions`, `triggers`, `types`, `sequences`, `operators`

### Disable FK inference

```bash
db-schema-export --no-infer-fk
```

### Use FK mapping file

```bash
db-schema-export --fk-map ./fk_mappings.json
```

FK mapping JSON format:

```json
{
  "order_list.customer_id": "cust_master.cid",
  "public.shift_master.studio_id": "public.studio.stdid"
}
```

### Export with AI analysis

```bash
db-schema-export --analyze
```

### Run AI analysis standalone

```bash
db-schema-analyze path/to/schema.md
db-schema-analyze path/to/schema.md --output ./analysis
db-schema-analyze path/to/schema.md --model Qwen/Qwen3-1.7B
```

### Run as Python module

```bash
python -m db_schema_export --output ./docs
```

## Output

For each database, the tool generates:

| File | Description |
|---|---|
| `{database}_schema.md` | Full schema documentation in Markdown |
| `{database}_erd.png` | High-resolution ERD diagram image (requires mermaid-cli) |
| `{database}_schema_analysis.md` | AI-generated analysis (with `--analyze`) |

### Schema Markdown structure

```
# {database} - Database Schema
├── Table of Contents
├── ERD Diagram (Mermaid)
├── Tables (columns, types, keys, defaults, comments)
├── Views (SQL definitions)
├── Functions/Procedures (arguments, return types, language)
├── Triggers (timing, events, functions)
├── Types (custom types with definitions)
├── Sequences (start, increment, owned by)
└── Operators (custom operators with types)
```

## FK Inference Engine

The engine infers foreign key relationships using 4 matching levels:

| Level | Confidence | Example |
|---|---|---|
| Exact match | High | `user_id` → table `user` |
| Plural match | Medium | `user_id` → table `users` |
| Suffix variant | Medium | `store_id` → table `store_master` |
| Short name fuzzy | Low | `uid` → table `users` |

Inferred relationships are shown as dashed lines in the ERD diagram. Confirmed FK constraints use solid lines.

## ERD Image Export

Requires [mermaid-cli](https://github.com/mermaid-js/mermaid-cli):

```bash
npm install -g @mermaid-js/mermaid-cli
```

Images are exported at 4x scale (high DPI) for readability on large diagrams.

## AI Analysis

The AI analyzer uses Qwen3-1.7B to produce detailed schema analysis reports covering:
- Database overview and purpose
- Table roles and relationships
- Data flow patterns
- Design observations

Requirements:

```bash
pip install transformers torch accelerate
```

The model is downloaded and cached in `.cache/` on first run.

## Kiro Skills

This project includes two Kiro skills for interactive database analysis.

### db-schema-analyst

A skill that analyzes database structure from exported Markdown schema files.

#### Activation

In Kiro chat, type `#db-schema-analyst` to load the skill into context, then request analysis:

```
#db-schema-analyst Analyze the database schema for me
```

#### Workflow

1. **Select files**: The AI agent will ask you to choose the markdown schema file(s) to analyze (supports multiple files)
2. **Select language(s)**: Choose output language(s) (supports multiple languages simultaneously)
   - Example: "Vietnamese and Japanese" → generates 2 separate files
3. **Receive results**: The AI agent reads the schema file and creates a detailed analysis report

#### Example

```
User: #db-schema-analyst Analyze outputs/mydb_schema.md in Vietnamese and English

Agent: I will analyze outputs/mydb_schema.md and create 2 reports:
       - outputs/analyst_mydb_schema_vi.md (Vietnamese)
       - outputs/analyst_mydb_schema_en.md (English)
```

#### Analysis report contents

The report includes 11 sections:

| # | Section | Content |
|---|---|---|
| 1 | Database Overview | Purpose, tech stack, scale |
| 2 | Table Analysis | Grouped by business domain, role of each table |
| 3 | Views Analysis | Purpose, source tables, use cases |
| 4 | Functions/Procedures | Purpose, input/output, business logic |
| 5 | Triggers Analysis | Table, triggering events, processing logic |
| 6 | Types Analysis | Custom types, values, usage |
| 7 | Sequences Analysis | Sequences, owning tables, values |
| 8 | Operators Analysis | Custom operators, data types |
| 9 | Relationship Analysis | Confirmed and inferred FKs |
| 10 | Data Flow | Main business flows |
| 11 | Design Notes | Patterns, integrations, notes |

#### Output file naming

```
analyst_[original_filename].md           # Single language
analyst_[original_filename]_vi.md        # Vietnamese
analyst_[original_filename]_en.md        # English
analyst_[original_filename]_ja.md        # Japanese
```

Output files are placed in the same directory as the source schema file.

### db-knowledge-graph

A skill that generates a knowledge graph (JSON) from database schema or analysis files.

#### Activation

```
#db-knowledge-graph Generate knowledge graph for the database
```

#### Workflow

1. **Select files**: Choose the schema or analysis markdown file(s)
2. **Select detail level**: `summary` (tables + relationships only) or `detailed` (includes functions, triggers, sequences, operators, views)
3. **Receive results**: JSON file with nodes, edges, and tour (business flow walkthrough)

#### Output structure

```json
{
  "version": "1.0.0",
  "project": { "name": "...", "description": "...", "analyzedAt": "...", "source": "..." },
  "nodes": [
    { "id": "table:public.users", "type": "table", "name": "users", "summary": "...", "tags": [...], "complexity": "..." }
  ],
  "edges": [
    { "source": "table:public.users", "target": "table:public.sessions", "type": "inferred_fk", "direction": "forward", "weight": 0.8 }
  ],
  "tour": [
    { "order": 1, "title": "User Registration Flow", "description": "...", "nodeIds": [...] }
  ]
}
```

#### Node types

| Type | Description |
|---|---|
| `table` | Database table |
| `view` | Database view |
| `function` | Function/Procedure |
| `trigger` | Trigger |
| `type` | Custom type |
| `sequence` | Sequence |
| `operator` | Custom operator |
| `column` | Column (PK/FK only, detailed mode) |
| `schema` | Schema |
| `business_group` | Business domain group |
| `external_system` | External integration |

#### Edge types

| Type | Description | Weight |
|---|---|---|
| `foreign_key` | Confirmed FK | 1.0 |
| `inferred_fk` | Inferred FK | 0.6-0.8 |
| `contains` | Table contains trigger | 1.0 |
| `calls` | Trigger calls function | 1.0 |
| `belongs_to` | Belongs to group/schema | 0.2-0.4 |
| `data_flow` | Business data flow | 0.6 |
| `integrates_with` | External system integration | 0.6 |
| `uses` | Table uses sequence | 0.2 |
| `depends_on` | View depends on table | 0.8 |

#### Output file naming

```
knowledge_graph_[original_filename].json
```

## Project Structure

```
db_schema_export/
├── __init__.py              # Package init
├── __main__.py              # Entry point (python -m)
├── cli.py                   # CLI argument parsing & orchestration
├── env_parser.py            # .env file parser
├── db_connector.py          # PostgreSQL connection management
├── metadata_collector.py    # Schema metadata collection queries
├── fk_inference_engine.py   # FK relationship inference
├── markdown_generator.py    # Markdown output generation
├── ai_analyzer.py           # AI-powered schema analysis
├── models.py                # Data models (dataclasses)
├── exceptions.py            # Custom exception classes
├── system_prompt.txt        # AI system prompt
├── requirements.txt         # Dependencies
└── tests/                   # Test suite
    ├── conftest.py
    ├── test_cli.py
    ├── test_db_connector.py
    ├── test_exceptions.py
    ├── test_integration.py
    └── test_models.py
```

## Development

### Run tests

```bash
pytest
```

### Run tests with coverage

```bash
pytest --cov=db_schema_export --cov-report=term-missing
```

## Exit Codes

| Code | Meaning |
|---|---|
| 0 | Success (all databases processed) |
| 1 | Fatal error (config error, all databases failed) |
| 2 | Partial success (some databases failed, some output generated) |

## License

MIT
