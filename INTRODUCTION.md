# DB Schema Export — Project Introduction

> 🌐 Language: **English** | [日本語](INTRODUCTION.ja.md) | [Tiếng Việt](INTRODUCTION.vi.md)

## Background

In real-world software projects, databases often evolve over many years by different teams. The result is a complex database system with hundreds of tables, thousands of columns, implicit relationships (without FK constraints), domain-specific naming conventions, and integrations with many external systems.

When new developers join a project, or when a database review/audit is needed, understanding the entire database structure becomes a major challenge:

- **No up-to-date documentation**: Schema changes continuously but documentation cannot keep up
- **Implicit relationships**: Many FK relationships only exist at the application layer, without constraints on the DB
- **Hard-to-understand naming conventions**: Table/column names are abbreviated or use domain-specific terminology (e.g., `tenpo` = store, `kessai` = payment)
- **Lack of ERD diagrams**: No visual diagrams showing relationships between tables
- **Multilingual**: Multinational teams need documentation in multiple languages

## Solution

**DB Schema Export** is a tool that automates the entire pipeline from database connection → metadata collection → relationship inference → documentation generation → AI analysis → knowledge graph creation.

### Processing Pipeline

```
PostgreSQL Database
  ↓ (connect via .env)
Metadata Collector (collect schema)
  ↓
FK Inference Engine (infer relationships)
  ↓
Markdown Generator (generate documentation + ERD)
  ↓
AI Analyzer (analyze with Qwen3-1.7B)
  ↓
Knowledge Graph (JSON nodes/edges/tour)
```

### Main Components

| Component | Role |
|---|---|
| **Schema Export CLI** | Connect to PostgreSQL, collect metadata (tables, views, functions, triggers, types, sequences, operators), generate Markdown + ERD |
| **FK Inference Engine** | Infer FK relationships from naming conventions (4 confidence levels), support override via JSON mapping |
| **ERD Image Export** | Render Mermaid diagrams to high-resolution PNG |
| **AI Analyzer** | Analyze schema using LLM (Qwen3-1.7B) with streaming output |
| **Kiro Skills** | 2 interactive skills for detailed analysis and knowledge graph generation |

## Technologies Used

### Core

| Technology | Purpose |
|---|---|
| Python 3.9+ | Primary language |
| psycopg2 | PostgreSQL connection |
| python-dotenv | Read configuration from .env |
| Mermaid | Generate ERD diagrams |
| mermaid-cli (mmdc) | Render ERD to PNG |

### AI & Analysis

| Technology | Purpose |
|---|---|
| Hugging Face Transformers | Load and run LLM |
| Qwen3-1.7B | Schema analysis model (lightweight, runs locally) |
| PyTorch | Backend for inference |
| Accelerate | Optimize model loading |

### Development

| Technology | Purpose |
|---|---|
| pytest | Testing framework |
| pytest-cov | Code coverage |
| hypothesis | Property-based testing |

### Kiro Integration

| Component | Purpose |
|---|---|
| Kiro Skills | Guide AI agent to perform interactive analysis |
| Batch Processing | Process large files by splitting into batches |
| Knowledge Graph | Structured JSON output for visualization |

## Use Cases

### 1. Onboarding new developers

When new developers join a project, instead of spending weeks reading code and asking colleagues, they can:
- Read analysis files (analyst_*.md) to understand the database overview
- View ERD diagrams to grasp relationships between tables
- Follow "tours" in the knowledge graph to understand business flows

### 2. Code review & Audit

When database changes need to be reviewed or security audited:
- Documentation is automatically updated each time the tool is run
- FK inference detects implicit relationships that developers might miss
- Knowledge graph clearly shows data flow and external integration points

### 3. Multilingual documentation

With multinational teams (Japanese - Vietnamese - English):
- Generate documentation in one source language, then translate automatically
- Keep technical names unchanged, only translate descriptions
- Ensure all team members understand the database

### 4. Knowledge Graph for AI/Tool integration

The JSON knowledge graph file can be used by:
- **Visualization tools**: Render interactive graphs (D3.js, Cytoscape, Neo4j)
- **AI agents**: Provide database context to LLMs during code generation
- **Documentation platforms**: Import into Confluence, Notion, or custom wikis
- **Impact analysis**: Analyze the impact when schema changes occur

### 5. Detecting design issues

Through automated analysis, the tool can detect:
- Tables without a PK
- Implicit relationships missing FK constraints
- Inconsistent naming conventions
- Orphan tables (no relationships with any other table)
- Missing indexes on FK columns

## Impact on the FEELCYCLE Project

This project was developed in the context of the FEELCYCLE fitness studio chain management system — a complex system with:

- **3 database environments**: Development (mobile app), Staging, Test
- **100+ tables** in each staging/test database
- **Multi-system integration**: Salesforce (CRM), GMO Payment Gateway (payment), Heroku Connect (synchronization)
- **Japanese naming conventions**: `tenpo`, `kessai`, `araigae`, `kubun`...
- **Multinational team**: Needs documentation in Vietnamese and Japanese

### Results Achieved

| Output | Quantity | Description |
|---|---|---|
| Schema Markdown | 3 files | Complete documentation for 3 databases |
| ERD Diagram | 3 PNG files | Visual relationship diagrams |
| Detailed Analysis | 6 files (3 DBs × 2 languages) | 11-section reports in Vietnamese and Japanese |
| Knowledge Graph | 3 JSON files | 45-128 nodes, 55-117 edges, 4-5 tours per file |

### Value Delivered

1. **Time savings**: From weeks down to minutes to understand the database
2. **Always up-to-date documentation**: Re-run the tool whenever the schema changes
3. **Reduced language barriers**: Automatic multilingual documentation
4. **Discovering hidden relationships**: FK inference finds relationships without constraints
5. **AI development support**: Knowledge graph provides context for AI agents

## Output Structure

```
outputs/
├── feelcycle-mob-db-dev_schema.md              # Schema documentation
├── feelcycle-mob-db-dev_erd.png                # ERD diagram
├── analyst_feelcycle-mob-db-dev_schema_vi.md   # Analysis (Vietnamese)
├── analyst_feelcycle-mob-db-dev_schema_ja.md   # Analysis (Japanese)
├── knowledge_graph_feelcycle-mob-db-dev_schema.json  # Knowledge graph
├── feelcycle-stg-db-base_schema.md
├── feelcycle-stg-db-base_erd.png
├── analyst_feelcycle-stg-db-base_schema_vi.md
├── analyst_feelcycle-stg-db-base_schema_ja.md
├── knowledge_graph_feelcycle-stg-db-base_schema.json
├── feelcycle-stg-db-test-base_schema.md
├── feelcycle-stg-db-test-base_erd.png
├── analyst_feelcycle-stg-db-test-base_schema_vi.md
├── analyst_feelcycle-stg-db-test-base_schema_ja.md
└── knowledge_graph_feelcycle-stg-db-test-base_schema.json
```

## Future Development

- **Support additional DBMS**: MySQL, SQL Server, Oracle
- **Diff detection**: Compare schema between 2 points in time, highlight changes
- **Interactive visualization**: Web UI to render interactive knowledge graphs
- **CI/CD integration**: Automatically generate documentation when migrations run
- **Schema recommendation**: AI suggests design improvements (indexes, constraints, normalization)
