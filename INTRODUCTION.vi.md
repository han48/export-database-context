# DB Schema Export — Giới thiệu dự án

> 🌐 Language: [English](INTRODUCTION.md) | [日本語](INTRODUCTION.ja.md) | **Tiếng Việt**

## Bối cảnh

Trong các dự án phần mềm thực tế, database thường phát triển qua nhiều năm bởi nhiều đội ngũ khác nhau. Kết quả là một hệ thống database phức tạp với hàng trăm bảng, hàng nghìn cột, các quan hệ ngầm (không có FK constraint), naming convention đặc thù theo domain, và tích hợp với nhiều hệ thống bên ngoài.

Khi developer mới tham gia dự án, hoặc khi cần review/audit database, việc hiểu toàn bộ cấu trúc database trở thành thách thức lớn:

- **Không có tài liệu cập nhật**: Schema thay đổi liên tục nhưng tài liệu không theo kịp
- **Quan hệ ngầm**: Nhiều FK relationship chỉ tồn tại ở tầng application, không có constraint trên DB
- **Naming convention khó hiểu**: Tên bảng/cột viết tắt hoặc dùng thuật ngữ domain đặc thù (ví dụ: `tenpo` = cửa hàng, `kessai` = thanh toán)
- **Thiếu ERD diagram**: Không có sơ đồ trực quan thể hiện quan hệ giữa các bảng
- **Đa ngôn ngữ**: Đội ngũ đa quốc gia cần tài liệu bằng nhiều ngôn ngữ

## Giải pháp

**DB Schema Export** là công cụ tự động hóa toàn bộ quy trình từ kết nối database → thu thập metadata → suy luận quan hệ → tạo tài liệu → phân tích bằng AI → tạo knowledge graph.

### Pipeline xử lý

```
PostgreSQL Database
  ↓ (kết nối qua .env)
Metadata Collector (thu thập schema)
  ↓
FK Inference Engine (suy luận quan hệ)
  ↓
Markdown Generator (tạo tài liệu + ERD)
  ↓
AI Analyzer (phân tích bằng Qwen3-1.7B)
  ↓
Knowledge Graph (JSON nodes/edges/tour)
```

### Các thành phần chính

| Thành phần | Vai trò |
|---|---|
| **Schema Export CLI** | Kết nối PostgreSQL, thu thập metadata (bảng, view, function, trigger, type, sequence, operator), tạo Markdown + ERD |
| **FK Inference Engine** | Suy luận quan hệ FK từ naming convention (4 mức độ tin cậy), hỗ trợ override bằng JSON mapping |
| **ERD Image Export** | Render sơ đồ Mermaid thành PNG độ phân giải cao |
| **AI Analyzer** | Phân tích schema bằng LLM (Qwen3-1.7B) với streaming output |
| **Kiro Skills** | 2 skill tương tác cho phân tích chi tiết và tạo knowledge graph |

## Công nghệ sử dụng

### Core

| Công nghệ | Mục đích |
|---|---|
| Python 3.9+ | Ngôn ngữ chính |
| psycopg2 | Kết nối PostgreSQL |
| python-dotenv | Đọc cấu hình từ .env |
| Mermaid | Tạo ERD diagram |
| mermaid-cli (mmdc) | Render ERD thành PNG |

### AI & Analysis

| Công nghệ | Mục đích |
|---|---|
| Hugging Face Transformers | Load và chạy LLM |
| Qwen3-1.7B | Model phân tích schema (nhẹ, chạy local) |
| PyTorch | Backend cho inference |
| Accelerate | Tối ưu hóa model loading |

### Development

| Công nghệ | Mục đích |
|---|---|
| pytest | Testing framework |
| pytest-cov | Code coverage |
| hypothesis | Property-based testing |

### Kiro Integration

| Thành phần | Mục đích |
|---|---|
| Kiro Skills | Hướng dẫn AI agent thực hiện phân tích tương tác |
| Batch Processing | Xử lý file lớn bằng cách chia nhỏ thành batch |
| Knowledge Graph | Output JSON có cấu trúc cho visualization |

## Ý nghĩa sử dụng

### 1. Onboarding developer mới

Khi developer mới tham gia dự án, thay vì mất hàng tuần đọc code và hỏi đồng nghiệp, họ có thể:
- Đọc file phân tích (analyst_*.md) để hiểu tổng quan database
- Xem ERD diagram để nắm quan hệ giữa các bảng
- Theo dõi "tour" trong knowledge graph để hiểu luồng nghiệp vụ

### 2. Code review & Audit

Khi cần review thay đổi database hoặc audit bảo mật:
- Tài liệu tự động cập nhật mỗi khi chạy tool
- FK inference phát hiện quan hệ ngầm mà developer có thể bỏ sót
- Knowledge graph thể hiện rõ data flow và điểm tích hợp bên ngoài

### 3. Tài liệu đa ngôn ngữ

Với đội ngũ đa quốc gia (Nhật - Việt - Anh):
- Tạo tài liệu bằng 1 ngôn ngữ gốc, sau đó dịch tự động
- Giữ nguyên tên kỹ thuật, chỉ dịch phần mô tả
- Đảm bảo tất cả thành viên đều hiểu database

### 4. Knowledge Graph cho AI/Tool integration

File JSON knowledge graph có thể được sử dụng bởi:
- **Visualization tools**: Render đồ thị tương tác (D3.js, Cytoscape, Neo4j)
- **AI agents**: Cung cấp context về database cho LLM khi code generation
- **Documentation platforms**: Import vào Confluence, Notion, hoặc custom wiki
- **Impact analysis**: Phân tích ảnh hưởng khi thay đổi schema

### 5. Phát hiện vấn đề thiết kế

Qua phân tích tự động, tool có thể phát hiện:
- Bảng không có PK
- Quan hệ ngầm thiếu FK constraint
- Naming convention không nhất quán
- Bảng orphan (không có quan hệ với bảng nào)
- Thiếu index trên FK columns

## Tác dụng trong dự án FEELCYCLE

Dự án này được phát triển trong bối cảnh hệ thống quản lý chuỗi phòng tập FEELCYCLE — một hệ thống phức tạp với:

- **3 môi trường database**: Development (mobile app), Staging, Test
- **100+ bảng** trong mỗi database staging/test
- **Tích hợp đa hệ thống**: Salesforce (CRM), GMO Payment Gateway (thanh toán), Heroku Connect (đồng bộ)
- **Naming convention tiếng Nhật**: `tenpo`, `kessai`, `araigae`, `kubun`...
- **Đội ngũ đa quốc gia**: Cần tài liệu tiếng Việt và tiếng Nhật

### Kết quả đạt được

| Output | Số lượng | Mô tả |
|---|---|---|
| Schema Markdown | 3 file | Tài liệu đầy đủ cho 3 database |
| ERD Diagram | 3 file PNG | Sơ đồ quan hệ trực quan |
| Phân tích chi tiết | 6 file (3 DB × 2 ngôn ngữ) | Báo cáo 11 section bằng tiếng Việt và Nhật |
| Knowledge Graph | 3 file JSON | 45-128 nodes, 55-117 edges, 4-5 tours mỗi file |

### Giá trị mang lại

1. **Tiết kiệm thời gian**: Từ hàng tuần xuống còn vài phút để hiểu database
2. **Tài liệu luôn cập nhật**: Chạy lại tool mỗi khi schema thay đổi
3. **Giảm rào cản ngôn ngữ**: Tài liệu đa ngôn ngữ tự động
4. **Phát hiện quan hệ ẩn**: FK inference tìm ra quan hệ không có constraint
5. **Hỗ trợ AI development**: Knowledge graph cung cấp context cho AI agents

## Cấu trúc output

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

## Hướng phát triển

- **Hỗ trợ thêm DBMS**: MySQL, SQL Server, Oracle
- **Diff detection**: So sánh schema giữa 2 thời điểm, highlight thay đổi
- **Interactive visualization**: Web UI render knowledge graph tương tác
- **CI/CD integration**: Tự động tạo tài liệu khi migration chạy
- **Schema recommendation**: AI đề xuất cải thiện thiết kế (index, constraint, normalization)
