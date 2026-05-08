# Implementation Plan: Database Schema Export Tool

## Overview

Triển khai công cụ Python độc lập để xuất schema database PostgreSQL thành file Markdown. Công cụ đọc cấu hình từ file `.env`, truy vấn metadata database qua `information_schema` và `pg_catalog`, hỗ trợ FK inference, và sinh file Markdown chứa ERD (Mermaid), tables, views, functions, triggers.

## Tasks

- [x] 1. Khởi tạo project structure và data models
  - [x] 1.1 Tạo cấu trúc thư mục và file cơ bản
    - Tạo package `db_schema_export/` với `__init__.py`, `__main__.py`
    - Tạo `requirements.txt` với dependencies: psycopg2-binary, python-dotenv
    - Tạo `setup.py` hoặc `pyproject.toml` cho package installation
    - Tạo thư mục `db_schema_export/tests/` với `__init__.py` và `conftest.py`
    - _Requirements: 2.1_

  - [x] 1.2 Implement data models (`models.py`)
    - Tạo dataclasses: `ColumnMetadata`, `TableMetadata`, `ForeignKeyMetadata`, `ViewMetadata`, `FunctionMetadata`, `TriggerMetadata`, `SchemaMetadata`
    - Đảm bảo tất cả fields có type hints và default values theo design
    - _Requirements: 9.1, 9.2, 9.3, 9.4_

  - [x] 1.3 Implement custom exceptions (`exceptions.py`)
    - Tạo `EnvFileNotFoundError` với thông tin đường dẫn file
    - Tạo `MissingVariableError` với danh sách biến thiếu
    - Tạo `NoDatabaseError` khi không có DB_DATABASES hoặc DB_DATABASE
    - Tạo `DatabaseConnectionError` với host, port, database (không password)
    - Tạo `FKMappingFileError` cho lỗi đọc/parse FK mapping file (FKMapFileNotFoundError, FKMapParseError)
    - Tạo `SchemaNotFoundWarning` cho schema không tồn tại
    - Tạo `AllSchemasInvalidError` khi tất cả schema đều không hợp lệ
    - Tạo `MetadataQueryError` cho lỗi query metadata
    - Tạo `OutputWriteError` cho lỗi ghi file output
    - Implement error message format thống nhất: `[ERROR] {Type}: {Description} → {Details} → {Hint}`
    - _Requirements: 1.7, 1.8, 1.9, 2.3, 12.5, 12.6, 13.11, 13.12_

- [x] 2. Implement Env Parser
  - [x] 2.1 Implement `env_parser.py`
    - Implement function `parse_env(env_path: str) -> DbConfig`
    - Đọc file `.env` và extract các biến: DB_CONNECTION, DB_HOST, DB_PORT, DB_DATABASE, DB_USERNAME, DB_PASSWORD
    - Xử lý biến tùy chọn `DB_DATABASES` (comma-separated list, trim whitespace)
    - Fallback sang `DB_DATABASE` khi `DB_DATABASES` không tồn tại
    - Raise `EnvFileNotFoundError` khi file không tồn tại
    - Raise `MissingVariableError` khi thiếu biến bắt buộc
    - Raise `NoDatabaseError` khi không có database nào được chỉ định
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9_

  - [ ]* 2.2 Write unit tests cho env_parser (`tests/test_env_parser.py`)
    - Test parse thành công với đầy đủ biến
    - Test DB_DATABASES comma-separated parsing và trim whitespace
    - Test fallback sang DB_DATABASE khi DB_DATABASES không có
    - Test error khi file không tồn tại
    - Test error khi thiếu biến bắt buộc
    - Test error khi không có DB_DATABASES lẫn DB_DATABASE
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.7, 1.8, 1.9_

- [x] 3. Implement Database Connector
  - [x] 3.1 Implement abstract interface và PostgreSQL connector (`db_connector.py`)
    - Tạo abstract class `DatabaseConnector` với methods: `connect()`, `close()`, `execute_query()`
    - Implement context manager (`__enter__`, `__exit__`)
    - Implement `PostgresConnector` sử dụng psycopg2
    - Implement factory function `create_connector(config, database)` trả về connector phù hợp theo DB_CONNECTION
    - Xử lý connection errors với thông báo chứa host, port, database (không password)
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 10.10_

- [x] 4. Implement Metadata Collector
  - [x] 4.1 Implement `metadata_collector.py`
    - Implement class `MetadataCollector` với constructor nhận `DatabaseConnector`
    - Implement `get_schemas()` - lấy non-system schemas (loại trừ pg_catalog, information_schema, pg_toast)
    - Implement `get_tables(schemas)` - query tables với comments từ pg_catalog
    - Implement `get_columns(schema, table)` - query columns với comments, data types, nullable, defaults
    - Implement `get_primary_keys(schemas)` - query PK constraints
    - Implement `get_foreign_keys(schemas)` - query FK constraints
    - Implement `get_views(schemas)` - query view definitions
    - Implement `get_functions(schemas)` - query functions/procedures từ pg_catalog
    - Implement `get_triggers(schemas)` - query triggers từ information_schema
    - Implement `collect_all(schemas)` - orchestrate tất cả queries và trả về `SchemaMetadata`
    - Sử dụng các SQL queries đã định nghĩa trong design document
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8, 9.9, 12.1_

  - [ ]* 4.2 Write unit tests cho metadata_collector (`tests/test_metadata_collector.py`)
    - Mock database connector để test các query methods
    - Test `get_schemas()` loại trừ system schemas
    - Test `get_tables()` trả về đúng format TableMetadata
    - Test `get_columns()` mapping đúng data types và comments
    - Test `get_foreign_keys()` parse đúng FK relationships
    - Test `collect_all()` orchestration
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

- [x] 5. Checkpoint - Đảm bảo core modules hoạt động
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Implement FK Inference Engine
  - [x] 6.1 Implement `fk_inference_engine.py`
    - Implement class `FKInferenceEngine` với constructor nhận `tables` và optional `fk_mapping`
    - Implement `infer_all()` - chạy inference trên tất cả tables
    - Implement `_match_column_to_table()` với 4 mức matching theo thứ tự ưu tiên:
      1. Exact match: `{table_name}_id` → table `{table_name}` (confidence: high)
      2. Plural match: `{singular}_id` → table `{plural}` (confidence: medium)
      3. Suffix variant match: `{name}_id` → `{name}_master`, `{name}_mst` (confidence: medium)
      4. Short name fuzzy match: `uid` → `users` (confidence: low)
    - Implement `_apply_mapping_overrides()` - áp dụng FK mapping file overrides
    - Implement đọc và parse FK mapping file (JSON format)
    - Log inferred relationships với confidence indicators ra stdout
    - _Requirements: 13.1, 13.2, 13.3, 13.4, 13.5, 13.6, 13.7, 13.8, 13.9, 13.10, 13.13_

  - [ ]* 6.2 Write unit tests cho FK inference engine (`tests/test_fk_inference_engine.py`)
    - Test exact match: `user_id` → table `user`
    - Test plural match: `user_id` → table `users`
    - Test suffix variant: `store_id` → table `store_master`
    - Test short name fuzzy: `uid` → table `users`
    - Test FK mapping file override
    - Test column không match trả về None
    - Test confidence levels đúng cho mỗi loại match
    - _Requirements: 13.1, 13.2, 13.3, 13.4, 13.5, 13.6, 13.8, 13.9_

- [x] 7. Implement Markdown Generator
  - [x] 7.1 Implement `markdown_generator.py` - cấu trúc chính
    - Implement class `MarkdownGenerator` với constructor nhận metadata, relationships, sections, multi_schema flag
    - Implement `generate(output_path)` - sinh file Markdown hoàn chỉnh
    - Implement `_generate_toc()` - table of contents với anchor links
    - Implement logic chọn sections dựa trên tham số `--sections`
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 11.1, 11.2, 11.3_

  - [x] 7.2 Implement ERD section generation
    - Implement `_generate_erd_section()` - sinh Mermaid erDiagram syntax
    - Render tất cả tables như entities với columns và data types
    - Render explicit FK relationships bằng solid lines (`--`)
    - Render inferred relationships bằng dashed lines (`..`)
    - Xác định cardinality dựa trên nullable status và FK constraints
    - Thêm legend giải thích solid lines vs dashed lines
    - Xử lý tables không có relationships (standalone entities)
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 4.9, 4.10_

  - [x] 7.3 Implement Tables section generation
    - Implement `_generate_tables_section()` - chi tiết columns cho mỗi table
    - Render H3 heading cho mỗi table, hiển thị table comment
    - Render Markdown table với columns: Column Name, Data Type, Key (PK/FK), Not Null, Default Value, Comment
    - Prefix schema name khi multi_schema=True
    - Xử lý table không có columns
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

  - [x] 7.4 Implement Views, Functions, Triggers sections
    - Implement `_generate_views_section()` - view name, schema, SQL definition trong code block
    - Implement `_generate_functions_section()` - summary table với Schema, Function Name, Arguments, Return Type, Language, Type
    - Implement `_generate_triggers_section()` - table grouped by table name với Trigger Name, Table, Timing, Event, Function Called
    - Xử lý trường hợp không có views/functions/triggers (hiển thị "No ... found")
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 7.1, 7.2, 7.3, 7.4, 8.1, 8.2, 8.3, 8.4, 8.5, 8.6_

  - [ ]* 7.5 Write unit tests cho markdown_generator (`tests/test_markdown_generator.py`)
    - Test TOC generation với anchor links
    - Test ERD section sinh valid Mermaid syntax
    - Test solid lines cho confirmed FK, dashed lines cho inferred FK
    - Test Tables section render đúng Markdown table format
    - Test Views section với SQL code blocks
    - Test Functions section summary table
    - Test Triggers section grouped by table
    - Test empty sections hiển thị "No ... found"
    - Test sections filtering
    - _Requirements: 3.3, 3.4, 4.1, 4.5, 4.6, 5.3, 6.2, 6.3, 7.1, 8.2, 8.5_

- [x] 8. Checkpoint - Đảm bảo tất cả core modules hoạt động
  - Ensure all tests pass, ask the user if questions arise.

- [x] 9. Implement CLI và Entry Point
  - [x] 9.1 Implement `cli.py`
    - Implement `parse_args()` với argparse cho tất cả CLI arguments:
      - `--output`: output directory (default: ".")
      - `--env`: path to .env file (default: ".env")
      - `--schema`: comma-separated schema list
      - `--sections`: comma-separated sections list (erd, tables, views, functions, triggers)
      - `--no-infer-fk`: disable FK inference
      - `--fk-map`: path to FK mapping file
    - Implement `main()` orchestration function:
      1. Parse arguments
      2. Parse .env file
      3. Loop qua mỗi database: connect → collect metadata → infer FK → generate markdown
      4. Hiển thị summary (số databases processed, danh sách file paths)
      5. Xử lý errors và exit codes (0=success, 1=fatal, 2=partial)
    - Implement graceful degradation:
      - Nếu một database fail → log error, tiếp tục với database khác
      - Nếu một schema không tồn tại → warning, tiếp tục với schema hợp lệ
      - Nếu một metadata query fail → log warning, tiếp tục thu thập loại khác
    - Validate `--fk-map` file tồn tại và parse được JSON
    - Validate `--schema` schemas tồn tại trong database
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7, 10.8, 10.9, 10.10, 12.2, 12.3, 12.4, 12.5, 12.6, 13.10, 13.11, 13.12_

  - [x] 9.2 Implement `__main__.py`
    - Tạo entry point cho `python -m db_schema_export`
    - Import và gọi `main()` từ `cli.py`
    - _Requirements: 10.10_

- [x] 10. Integration và final wiring
  - [x] 10.1 Tích hợp end-to-end flow
    - Đảm bảo pipeline hoàn chỉnh: CLI → EnvParser → DBConnector → MetadataCollector → FKInference → MarkdownGenerator
    - Xử lý multi-database flow (loop qua DB_DATABASES)
    - Xử lý multi-schema flow (prefix schema names, detect non-system schemas)
    - Đảm bảo file output naming đúng pattern `{database_name}_schema.md`
    - Đảm bảo overwrite file nếu đã tồn tại
    - _Requirements: 1.6, 3.1, 3.2, 9.10, 11.1, 11.2, 11.3, 12.1, 12.4_

  - [ ]* 10.2 Write integration tests
    - Test full pipeline với mock database
    - Test multi-database output tạo đúng số file
    - Test CLI argument combinations
    - Test error handling end-to-end
    - _Requirements: 1.6, 3.2, 10.7, 10.8, 10.9_

- [x] 11. Final checkpoint - Đảm bảo tất cả tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks đánh dấu `*` là optional và có thể bỏ qua để đẩy nhanh MVP
- Mỗi task tham chiếu đến requirements cụ thể để đảm bảo traceability
- Checkpoints đảm bảo validation tăng dần
- Unit tests validate specific examples và edge cases
- Design document đã cung cấp đầy đủ SQL queries và algorithm details cho implementation
