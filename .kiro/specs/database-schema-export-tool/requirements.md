# Requirements Document

## Introduction

Công cụ Python độc lập để xuất schema database thành file Markdown (.md) toàn diện. Công cụ đọc cấu hình kết nối database từ file `.env` của dự án Laravel hiện tại, hỗ trợ PostgreSQL và có khả năng mở rộng cho MySQL trong tương lai. Công cụ truy vấn trực tiếp metadata của database mà không sử dụng AI Agent.

Công cụ hỗ trợ xử lý nhiều database cùng lúc thông qua biến `DB_DATABASES` (danh sách database phân cách bằng dấu phẩy). Khi xử lý nhiều database, công cụ tạo một file .md riêng cho mỗi database. Nếu `DB_DATABASES` không được định nghĩa, công cụ sử dụng `DB_DATABASE` (hành vi tương thích ngược).

File Markdown output bao gồm các section:
1. ERD Diagram (Mermaid erDiagram - tables và relationships) + ERD image export (PNG)
2. Tables (thông tin chi tiết columns, types, keys, comments cho mỗi bảng)
3. Views (danh sách views với definitions)
4. Functions/Procedures (danh sách với signatures)
5. Triggers (bảng nào, event nào, timing, function được gọi)
6. Types (custom types: enum, composite, domain, range)
7. Sequences (danh sách sequences với properties)
8. Operators (custom operators với types và functions)

Công cụ hỗ trợ xuất thông tin từ nhiều schema khác nhau (ví dụ: public, salesforce).

## Glossary

- **Schema_Export_Tool**: Công cụ Python độc lập thực hiện việc xuất schema database
- **Database_Connector**: Module chịu trách nhiệm kết nối đến database dựa trên cấu hình từ file .env
- **Markdown_Generator**: Module chịu trách nhiệm tạo file Markdown chứa toàn bộ thông tin schema (ERD, tables, views, functions, triggers)
- **Env_Parser**: Module chịu trách nhiệm đọc và phân tích file .env
- **DB_DATABASES**: Biến môi trường tùy chọn trong file .env chứa danh sách database phân cách bằng dấu phẩy. Khi được định nghĩa, công cụ xử lý tất cả database trong danh sách. Tất cả database dùng chung host, port, username, password
- **Schema_Metadata**: Thông tin metadata của database bao gồm tên bảng, cột, kiểu dữ liệu, khóa, ràng buộc, quan hệ giữa các bảng, views, functions, triggers, và comments
- **FK_Inference_Engine**: Module chịu trách nhiệm dự đoán foreign key relationships dựa trên quy ước đặt tên cột khi database không có FK constraints tường minh
- **FK_Mapping_File**: File cấu hình (JSON hoặc YAML) cho phép người dùng định nghĩa hoặc ghi đè các FK relationships thủ công
- **Inferred_Relationship**: Quan hệ FK được dự đoán bởi FK_Inference_Engine dựa trên naming conventions, chưa được xác nhận bởi database constraints
- **Database_Schema**: Một namespace logic trong database chứa các đối tượng (tables, views, functions, triggers). Ví dụ: "public", "salesforce"
- **View_Metadata**: Thông tin về views bao gồm tên view, schema chứa view, và định nghĩa SQL của view
- **Function_Metadata**: Thông tin về functions/procedures bao gồm tên function, schema, tham số đầu vào, kiểu trả về, và ngôn ngữ lập trình (plpgsql, sql)
- **Trigger_Metadata**: Thông tin về triggers bao gồm tên trigger, bảng gắn trigger, event kích hoạt (INSERT/UPDATE/DELETE), timing (BEFORE/AFTER/INSTEAD OF), và function được gọi
- **Type_Metadata**: Thông tin về custom types bao gồm tên type, schema, loại (enum/composite/domain/range), và định nghĩa (enum labels, base type)
- **Sequence_Metadata**: Thông tin về sequences bao gồm tên sequence, schema, data type, start value, increment, và column sở hữu
- **Operator_Metadata**: Thông tin về custom operators bao gồm tên operator, schema, left/right operand types, result type, và function thực thi

## Requirements

### Requirement 1: Đọc cấu hình database từ file .env

**User Story:** As a developer, I want the tool to read database configuration from the existing Laravel .env file, so that I don't need to configure connection details separately.

#### Acceptance Criteria

1. WHEN the Schema_Export_Tool is executed, THE Env_Parser SHALL read the file `.env` tại thư mục gốc của dự án
2. THE Env_Parser SHALL extract the following variables: DB_CONNECTION, DB_HOST, DB_PORT, DB_DATABASE, DB_USERNAME, DB_PASSWORD
3. THE Env_Parser SHALL extract the optional variable DB_DATABASES as a comma-separated list of database names (e.g., `DB_DATABASES=feelcycle_stg,feelcycle_prod,another_db`)
4. WHEN DB_DATABASES is defined in the `.env` file, THE Env_Parser SHALL parse the value as a comma-separated list and trim whitespace from each database name
5. WHEN DB_DATABASES is not defined in the `.env` file, THE Env_Parser SHALL fall back to using DB_DATABASE as the single target database (backward compatible behavior)
6. WHEN DB_DATABASES is defined, THE Schema_Export_Tool SHALL process all databases in the list using the shared connection parameters (DB_HOST, DB_PORT, DB_USERNAME, DB_PASSWORD)
7. IF the `.env` file does not exist at the project root, THEN THE Env_Parser SHALL display an error message indicating the file path that was searched
8. IF any required database variable (DB_CONNECTION, DB_HOST, DB_PORT, DB_USERNAME, DB_PASSWORD) is missing from the `.env` file, THEN THE Env_Parser SHALL display an error message listing the missing variables
9. IF neither DB_DATABASES nor DB_DATABASE is defined in the `.env` file, THEN THE Env_Parser SHALL display an error message indicating that at least one database must be specified
10. WHEN DB_CONNECTION is "pgsql", THE Database_Connector SHALL connect using PostgreSQL driver
11. WHEN DB_CONNECTION is "mysql", THE Database_Connector SHALL connect using MySQL driver

### Requirement 2: Kết nối database với kiến trúc mở rộng

**User Story:** As a developer, I want the tool to support PostgreSQL now and be extensible for MySQL in the future, so that the tool can work with different database systems.

#### Acceptance Criteria

1. THE Database_Connector SHALL implement a common interface for database operations regardless of the underlying database type
2. WHEN connecting to PostgreSQL, THE Database_Connector SHALL use the psycopg2 library
3. IF the database connection fails, THEN THE Database_Connector SHALL display an error message containing the host, port, and database name (without exposing the password)
4. THE Database_Connector SHALL provide methods to retrieve table list, column information, foreign key relationships, views, functions, and triggers through the common interface
5. WHERE MySQL support is enabled, THE Database_Connector SHALL use the mysql-connector-python library

### Requirement 3: Tạo file Markdown toàn diện chứa thông tin schema

**User Story:** As a developer, I want to generate a comprehensive Markdown file containing ERD diagram, table details, views, functions, and triggers, so that I can have complete database documentation in a single readable file.

#### Acceptance Criteria

1. WHEN the Schema_Export_Tool is executed, THE Markdown_Generator SHALL create a .md file in the output directory for each target database
2. WHEN multiple databases are configured (via DB_DATABASES), THE Markdown_Generator SHALL generate one separate .md file per database
3. THE Markdown_Generator SHALL structure the output file with the following sections in order: ERD Diagram, Tables, Views, Functions/Procedures, Triggers, Types, Sequences, Operators
4. THE Markdown_Generator SHALL include a table of contents at the beginning of the file with links to each section
5. THE Markdown_Generator SHALL use proper Markdown heading hierarchy (H1 for title, H2 for main sections, H3 for individual objects)

### Requirement 4: Section ERD Diagram (Mermaid erDiagram)

**User Story:** As a developer, I want the Markdown file to include a Mermaid erDiagram showing tables and their relationships, so that I can visualize the database relationships directly in documentation tools.

#### Acceptance Criteria

1. THE Markdown_Generator SHALL generate a valid Mermaid erDiagram syntax block wrapped in ```mermaid code fence in the ERD Diagram section
2. THE Markdown_Generator SHALL include all tables from the selected schema(s) as entities in the erDiagram
3. FOR each entity, THE Markdown_Generator SHALL list all columns with their data types
4. THE Markdown_Generator SHALL determine relationships between tables from two sources: explicit foreign key constraints from database metadata, and Inferred_Relationships from the FK_Inference_Engine
5. THE Markdown_Generator SHALL represent explicit foreign key relationships using solid relationship lines with correct Mermaid relationship notation (||--o{, ||--|{, etc.)
6. THE Markdown_Generator SHALL represent Inferred_Relationships using dashed relationship lines in the Mermaid erDiagram, with a comment annotation indicating "inferred"
7. THE Markdown_Generator SHALL determine relationship cardinality based on foreign key constraints, nullable status, and inference rules
8. IF a table has no explicit foreign key relationships and no Inferred_Relationships, THEN THE Markdown_Generator SHALL include the table as a standalone entity without relationship lines
9. THE Markdown_Generator SHALL include a legend or note in the ERD section explaining the difference between solid lines (confirmed FK) and dashed lines (inferred FK)
10. THE Markdown_Generator SHALL focus exclusively on tables and their relationships in the ERD section; views, functions, and triggers are in separate sections

### Requirement 5: Section Tables (chi tiết columns)

**User Story:** As a developer, I want the Markdown file to include detailed column information for each table, so that I can review table structures without connecting to the database.

#### Acceptance Criteria

1. THE Markdown_Generator SHALL create a subsection (H3) for each table in the selected schema(s)
2. FOR each table, THE Markdown_Generator SHALL display table comment (if available) below the table heading
3. FOR each table, THE Markdown_Generator SHALL render a Markdown table with columns: Column Name, Data Type, Key (PK/FK), Not Null, Default Value, Comment
4. THE Markdown_Generator SHALL prefix table names with schema name when exporting from multiple schemas (e.g., `public.users`)
5. IF a table has no columns (empty table metadata), THEN THE Markdown_Generator SHALL display a note "No columns found" under the table heading

### Requirement 6: Section Views

**User Story:** As a developer, I want the Markdown file to include view definitions, so that I can document and review all views alongside tables.

#### Acceptance Criteria

1. THE Markdown_Generator SHALL create a subsection for each view in the selected schema(s)
2. FOR each view, THE Markdown_Generator SHALL display the view name, schema, and SQL definition in a code block
3. IF no views exist in the selected schema(s), THEN THE Markdown_Generator SHALL display a note "No views found" in the Views section
4. THE Markdown_Generator SHALL retrieve view column information including column name and data type for each view

### Requirement 7: Section Functions/Procedures

**User Story:** As a developer, I want the Markdown file to include function and procedure information, so that I can document all database logic including trigger functions and utility functions.

#### Acceptance Criteria

1. THE Markdown_Generator SHALL create a summary Markdown table listing all functions with columns: Schema, Function Name, Arguments, Return Type, Language, Type (function/trigger/procedure)
2. THE Schema_Export_Tool SHALL classify functions by type: regular function, trigger function (returns trigger), or procedure
3. THE Markdown_Generator SHALL display function arguments in a readable format showing parameter name and data type (e.g., "price_without_tax integer, tax_rate numeric")
4. IF no functions exist in the selected schema(s), THEN THE Markdown_Generator SHALL display a note "No functions found" in the Functions section

### Requirement 8: Section Triggers

**User Story:** As a developer, I want the Markdown file to include trigger information, so that I can understand which triggers are attached to which tables, when they fire, and what functions they call.

#### Acceptance Criteria

1. THE Schema_Export_Tool SHALL query trigger metadata from the selected schema(s) including trigger name, table name, event (INSERT/UPDATE/DELETE), timing (BEFORE/AFTER/INSTEAD OF), and the trigger function being called
2. THE Markdown_Generator SHALL render a Markdown table in the Triggers section with columns: Trigger Name, Table, Timing, Event, Function Called
3. THE Markdown_Generator SHALL group triggers by table for readability
4. THE Schema_Export_Tool SHALL query pg_catalog.pg_trigger to retrieve trigger definitions for the selected schema(s)
5. IF no triggers exist in the selected schema(s), THEN THE Markdown_Generator SHALL display a note "No triggers found" in the Triggers section
6. THE Schema_Export_Tool SHALL identify trigger functions (e.g., hc_*_logger, hc_*_status patterns) and link them to their corresponding triggers in the output

### Requirement 9: Truy vấn metadata trực tiếp từ database

**User Story:** As a developer, I want the tool to query database metadata directly without using any AI agent, so that the output is deterministic and accurate.

#### Acceptance Criteria

1. THE Schema_Export_Tool SHALL query pg_catalog to retrieve table metadata for the selected schema(s)
2. THE Schema_Export_Tool SHALL query pg_catalog to retrieve column metadata including column name, data type, nullable status, default value, and column comment
3. THE Schema_Export_Tool SHALL query pg_catalog to retrieve foreign key constraints including referencing table, referencing column, referenced table, and referenced column
4. THE Schema_Export_Tool SHALL query pg_catalog to retrieve primary key constraints
5. THE Schema_Export_Tool SHALL query pg_catalog.pg_description and pg_catalog.pg_class to retrieve table comments and column comments
6. THE Schema_Export_Tool SHALL query pg_catalog to retrieve view definitions for the selected schema(s)
7. THE Schema_Export_Tool SHALL query pg_catalog.pg_proc to retrieve function and procedure metadata for the selected schema(s)
8. THE Schema_Export_Tool SHALL query pg_catalog.pg_trigger to retrieve trigger metadata for the selected schema(s)
9. THE Schema_Export_Tool SHALL NOT use any AI service, LLM API, or external inference service to generate schema information or documentation content
10. IF no explicit foreign key constraints are found in the database, THEN THE Schema_Export_Tool SHALL activate the FK_Inference_Engine as a fallback mechanism to determine relationships between tables

### Requirement 10: Giao diện dòng lệnh (CLI)

**User Story:** As a developer, I want to run the tool from the command line with options, so that I can integrate it into my workflow and scripts.

#### Acceptance Criteria

1. THE Schema_Export_Tool SHALL accept a command-line argument `--output` to specify the output directory (default: current directory)
2. THE Schema_Export_Tool SHALL accept a command-line argument `--env` to specify the path to the .env file (default: ".env" in current directory)
3. THE Schema_Export_Tool SHALL accept a command-line argument `--schema` to specify which schema(s) to export as a comma-separated list (e.g., `--schema public,salesforce`). Default: all non-system schemas
4. THE Schema_Export_Tool SHALL accept a command-line argument `--sections` to specify which sections to include in the output as a comma-separated list (e.g., `--sections erd,tables,views,functions,triggers`). Default: all sections
5. THE Schema_Export_Tool SHALL accept a command-line argument `--no-infer-fk` to disable FK inference entirely
6. THE Schema_Export_Tool SHALL accept a command-line argument `--fk-map` to specify the path to a FK_Mapping_File for manual FK relationship definitions
7. WHEN execution completes successfully, THE Schema_Export_Tool SHALL display a summary message listing all generated files and their paths
8. WHEN multiple databases are processed, THE Schema_Export_Tool SHALL display the count of databases processed and list each generated file path in the summary
9. IF an error occurs during execution, THEN THE Schema_Export_Tool SHALL display a descriptive error message and exit with a non-zero exit code
10. THE Schema_Export_Tool SHALL display a help message when executed with --help flag

### Requirement 11: Đặt tên file output

**User Story:** As a developer, I want the output file to have a meaningful name, so that I can easily identify it.

#### Acceptance Criteria

1. THE Markdown_Generator SHALL name the output file using the pattern: `{database_name}_schema.md` for each target database
2. WHEN multiple databases are configured, THE Markdown_Generator SHALL generate one file per database, each named `{database_name}_schema.md` (e.g., `feelcycle_stg_schema.md`, `feelcycle_prod_schema.md`)
3. IF a file with the same name already exists in the output directory, THEN THE Schema_Export_Tool SHALL overwrite the existing file

### Requirement 12: Hỗ trợ nhiều schema

**User Story:** As a developer, I want the tool to support exporting from multiple database schemas (e.g., public, salesforce), so that I can get a complete picture of the database structure across all schemas.

#### Acceptance Criteria

1. THE Schema_Export_Tool SHALL detect all non-system schemas available in the database (excluding pg_catalog, information_schema, pg_toast)
2. WHEN the `--schema` argument is provided, THE Schema_Export_Tool SHALL export only the specified schema(s)
3. WHEN the `--schema` argument is not provided, THE Schema_Export_Tool SHALL export all non-system schemas
4. THE Schema_Export_Tool SHALL prefix object names with schema name when exporting from multiple schemas to avoid naming conflicts
5. IF a specified schema does not exist in the database, THEN THE Schema_Export_Tool SHALL display a warning message listing the invalid schema name and continue with valid schemas
6. IF none of the specified schemas exist, THEN THE Schema_Export_Tool SHALL display an error message and exit with a non-zero exit code

### Requirement 13: Dự đoán Foreign Key dựa trên Column Name

**User Story:** As a developer, I want the tool to infer foreign key relationships based on column naming conventions, so that the ERD diagram shows meaningful relationships even when the database has no explicit FK constraints defined.

#### Acceptance Criteria

1. WHEN no explicit foreign key constraints are found in the database, THE FK_Inference_Engine SHALL analyze column names to predict relationships between tables
2. WHEN a column is named `{table_name}_id` or `{table_name}id`, THE FK_Inference_Engine SHALL infer that the column references the `id` column of the table matching `{table_name}`
3. WHEN a column is named `{singular_table_name}_id`, THE FK_Inference_Engine SHALL attempt to match against existing table names including plural forms and suffixed variants (e.g., `store_id` matches `stores` or `store_master`)
4. WHEN a column name ends with `_id`, THE FK_Inference_Engine SHALL treat the column as a candidate for FK inference and attempt to match the prefix against all existing table names in the selected schema(s)
5. THE FK_Inference_Engine SHALL perform fuzzy matching for short column names: WHEN a column is named `uid`, THE FK_Inference_Engine SHALL check for tables named `user`, `users`, or `user_master`
6. THE FK_Inference_Engine SHALL mark all inferred relationships with a status of "inferred" to distinguish them from explicit FK constraints with status "confirmed"
7. WHEN the `--fk-map` argument is provided, THE Schema_Export_Tool SHALL read the FK_Mapping_File at the specified path to load manually defined FK relationships
8. THE FK_Mapping_File SHALL support JSON format with entries mapping `{schema.table.column}` or `{table.column}` to `{referenced_table.referenced_column}` (e.g., `{"account_cust.customer_id": "customer.id", "account_prod.at_customer_id": "account_cust.customer_id"}`)
9. WHEN a mapping in the FK_Mapping_File conflicts with an inferred relationship, THE Schema_Export_Tool SHALL use the mapping file definition as the authoritative source
10. WHEN the `--no-infer-fk` flag is provided, THE FK_Inference_Engine SHALL be disabled entirely and only explicit FK constraints from database metadata are used
11. IF the FK_Mapping_File path specified by `--fk-map` does not exist, THEN THE Schema_Export_Tool SHALL display a warning message indicating the file path and continue execution without FK mapping overrides
12. IF the FK_Mapping_File contains invalid JSON syntax, THEN THE Schema_Export_Tool SHALL display a parsing error message with line number information and exit with a non-zero exit code
13. THE FK_Inference_Engine SHALL log all inferred relationships to stdout with confidence indicators (e.g., "high" for exact table name match, "medium" for plural/suffix match, "low" for fuzzy match)

### Requirement 14: Section Types (custom database types)

**User Story:** As a developer, I want the Markdown file to include custom type definitions, so that I can document enum types, composite types, and domain types used in the database.

#### Acceptance Criteria

1. THE Schema_Export_Tool SHALL query pg_catalog.pg_type to retrieve custom type metadata for the selected schema(s)
2. THE Schema_Export_Tool SHALL classify types by category: enum, composite, domain, range
3. FOR enum types, THE Markdown_Generator SHALL display the list of enum labels
4. FOR domain types, THE Markdown_Generator SHALL display the base type
5. THE Markdown_Generator SHALL render a summary table with columns: Schema, Type Name, Category, Definition
6. IF no custom types exist in the selected schema(s), THEN THE Markdown_Generator SHALL display "No custom types found"

### Requirement 15: Section Sequences

**User Story:** As a developer, I want the Markdown file to include sequence information, so that I can understand auto-increment configurations and which columns own which sequences.

#### Acceptance Criteria

1. THE Schema_Export_Tool SHALL query pg_catalog.pg_sequence to retrieve sequence metadata for the selected schema(s)
2. THE Markdown_Generator SHALL render a summary table with columns: Schema, Sequence Name, Data Type, Start, Increment, Owned By
3. THE Schema_Export_Tool SHALL determine sequence ownership by querying pg_catalog.pg_depend
4. IF no sequences exist in the selected schema(s), THEN THE Markdown_Generator SHALL display "No sequences found"

### Requirement 16: Section Operators (custom operators)

**User Story:** As a developer, I want the Markdown file to include custom operator definitions, so that I can document non-standard operators used by extensions like hstore or PostGIS.

#### Acceptance Criteria

1. THE Schema_Export_Tool SHALL query pg_catalog.pg_operator to retrieve custom operator metadata for the selected schema(s)
2. THE Markdown_Generator SHALL render a summary table with columns: Schema, Operator, Left Type, Right Type, Result Type, Function
3. IF no custom operators exist in the selected schema(s), THEN THE Markdown_Generator SHALL display "No custom operators found"

### Requirement 17: Export ERD Diagram as high-resolution image

**User Story:** As a developer, I want the ERD diagram to be exported as a high-resolution PNG image, so that I can view and share the diagram without needing a Mermaid renderer, and zoom in on large diagrams without losing text clarity.

#### Acceptance Criteria

1. WHEN the ERD section is included and tables exist, THE Schema_Export_Tool SHALL export the Mermaid ERD diagram as a PNG image file
2. THE Schema_Export_Tool SHALL use mermaid-cli (mmdc) to render the diagram with a scale factor of 4x for high DPI output
3. THE Schema_Export_Tool SHALL name the ERD image file using the pattern: `{database_name}_erd.png`
4. THE Schema_Export_Tool SHALL use a viewport of 4096x4096 pixels to accommodate large diagrams with many tables
5. IF mmdc is not installed, THEN THE Schema_Export_Tool SHALL display a warning and continue without image export (graceful degradation)
6. IF the image export fails or times out (>120s), THEN THE Schema_Export_Tool SHALL display a warning and continue

### Requirement 18: Sử dụng pg_catalog thay vì information_schema

**User Story:** As a developer, I want the tool to use pg_catalog system tables directly for metadata queries, so that it can access all database objects regardless of user permission grants on information_schema views.

#### Acceptance Criteria

1. THE Schema_Export_Tool SHALL use pg_catalog.pg_namespace to detect available schemas (instead of information_schema.schemata)
2. THE Schema_Export_Tool SHALL use pg_catalog.pg_class to retrieve tables (instead of information_schema.tables)
3. THE Schema_Export_Tool SHALL use pg_catalog.pg_attribute to retrieve column metadata (instead of information_schema.columns)
4. THE Schema_Export_Tool SHALL use pg_catalog.pg_index to retrieve primary key information
5. THE Schema_Export_Tool SHALL use pg_catalog.pg_constraint to retrieve foreign key constraints
6. THE Schema_Export_Tool SHALL use pg_catalog.pg_class with pg_get_viewdef() to retrieve view definitions
7. THE Schema_Export_Tool SHALL use pg_catalog.pg_trigger to retrieve trigger metadata
8. THE Markdown_Generator SHALL sanitize data types for Mermaid ERD compatibility (removing parentheses, commas, and special characters)
9. THE Markdown_Generator SHALL output only one key marker per column in ERD (PK takes priority over FK when both apply)
