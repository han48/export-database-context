# DB Schema Export

> 🌐 Language: [English](README.md) | [日本語](README.ja.md) | **Tiếng Việt**

Xuất schema database PostgreSQL thành tài liệu Markdown toàn diện với sơ đồ ERD, suy luận FK, và phân tích bằng AI (tùy chọn).

## Tính năng

- **Xuất Schema**: Xuất toàn bộ schema database (bảng, view, function, trigger, type, sequence, operator) sang Markdown
- **Sơ đồ ERD**: Tự động tạo Mermaid erDiagram với quan hệ xác nhận và suy luận
- **Xuất ảnh ERD**: Render ERD thành PNG độ phân giải cao bằng mermaid-cli
- **Engine suy luận FK**: Tự động suy luận quan hệ foreign key dựa trên quy ước đặt tên (4 mức độ tin cậy)
- **Ghi đè FK Mapping**: Định nghĩa quan hệ FK thủ công qua file JSON
- **Hỗ trợ đa Database**: Xử lý nhiều database từ một file `.env`
- **Hỗ trợ đa Schema**: Xuất nhiều schema với prefix phù hợp
- **Lọc Section**: Chọn section nào cần đưa vào output
- **Phân tích AI** (tùy chọn): Phân tích schema bằng Qwen3-1.7B với streaming output

## Cài đặt

### Yêu cầu

- Python >= 3.9
- PostgreSQL database

### Cài đặt từ source

```bash
pip install -e .
```

### Cài đặt với hỗ trợ phân tích AI

```bash
pip install -e ".[ai]"
```

### Cài đặt với dependency phát triển

```bash
pip install -e ".[dev]"
```

## Cấu hình

Tạo file `.env` với cài đặt kết nối database:

```env
DB_CONNECTION=pgsql
DB_HOST=localhost
DB_PORT=5432
DB_USERNAME=postgres
DB_PASSWORD=your_password

# Một database
DB_DATABASE=my_database

# Hoặc nhiều database (phân cách bằng dấu phẩy)
DB_DATABASES=db_one, db_two, db_three
```

`DB_DATABASES` được ưu tiên hơn `DB_DATABASE` khi cả hai đều được định nghĩa.

## Sử dụng

### Xuất cơ bản

```bash
db-schema-export
```

### Chỉ định thư mục output và file env

```bash
db-schema-export --output ./docs --env .env.production
```

### Lọc schema

```bash
db-schema-export --schema public,salesforce
```

### Lọc section

```bash
db-schema-export --sections erd,tables,views
```

Các section hợp lệ: `erd`, `tables`, `views`, `functions`, `triggers`, `types`, `sequences`, `operators`

### Tắt suy luận FK

```bash
db-schema-export --no-infer-fk
```

### Sử dụng file FK mapping

```bash
db-schema-export --fk-map ./fk_mappings.json
```

Định dạng JSON FK mapping:

```json
{
  "order_list.customer_id": "cust_master.cid",
  "public.shift_master.studio_id": "public.studio.stdid"
}
```

### Xuất kèm phân tích AI

```bash
db-schema-export --analyze
```

### Chạy phân tích AI độc lập

```bash
db-schema-analyze path/to/schema.md
db-schema-analyze path/to/schema.md --output ./analysis
db-schema-analyze path/to/schema.md --model Qwen/Qwen3-1.7B
```

### Chạy dưới dạng Python module

```bash
python -m db_schema_export --output ./docs
```

## Output

Với mỗi database, tool tạo ra:

| File | Mô tả |
|---|---|
| `{database}_schema.md` | Tài liệu schema đầy đủ dạng Markdown |
| `{database}_erd.png` | Ảnh sơ đồ ERD độ phân giải cao (yêu cầu mermaid-cli) |
| `{database}_schema_analysis.md` | Phân tích do AI tạo (với `--analyze`) |

### Cấu trúc Markdown schema

```
# {database} - Database Schema
├── Mục lục
├── Sơ đồ ERD (Mermaid)
├── Bảng (cột, kiểu, khóa, giá trị mặc định, comment)
├── View (định nghĩa SQL)
├── Function/Procedure (tham số, kiểu trả về, ngôn ngữ)
├── Trigger (thời điểm, sự kiện, function)
├── Type (custom type với định nghĩa)
├── Sequence (start, increment, owned by)
└── Operator (custom operator với kiểu dữ liệu)
```

## Engine suy luận FK

Engine suy luận quan hệ foreign key sử dụng 4 mức độ matching:

| Mức độ | Độ tin cậy | Ví dụ |
|---|---|---|
| Khớp chính xác | Cao | `user_id` → bảng `user` |
| Khớp số nhiều | Trung bình | `user_id` → bảng `users` |
| Khớp biến thể suffix | Trung bình | `store_id` → bảng `store_master` |
| Khớp mờ tên viết tắt | Thấp | `uid` → bảng `users` |

Quan hệ suy luận hiển thị bằng đường nét đứt trong sơ đồ ERD. Ràng buộc FK xác nhận dùng đường nét liền.

## Xuất ảnh ERD

Yêu cầu [mermaid-cli](https://github.com/mermaid-js/mermaid-cli):

```bash
npm install -g @mermaid-js/mermaid-cli
```

Ảnh được xuất ở tỷ lệ 4x (DPI cao) để đảm bảo đọc được trên sơ đồ lớn.

## Phân tích AI

AI analyzer sử dụng Qwen3-1.7B để tạo báo cáo phân tích schema chi tiết bao gồm:
- Tổng quan và mục đích database
- Vai trò và quan hệ giữa các bảng
- Pattern luồng dữ liệu
- Nhận xét về thiết kế

Yêu cầu:

```bash
pip install transformers torch accelerate
```

Model được tải và cache trong `.cache/` ở lần chạy đầu tiên.

## Kiro Skills

Project này bao gồm một Kiro skill cho phân tích schema database tương tác.

### db-schema-analyst

Skill phân tích cấu trúc database từ file Markdown schema đã export.

#### Kích hoạt

Trong Kiro chat, gõ `#db-schema-analyst` để load skill vào context, sau đó yêu cầu phân tích:

```
#db-schema-analyst Phân tích database schema cho tôi
```

#### Quy trình

1. **Chọn file**: AI agent sẽ hỏi bạn chọn file markdown schema cần phân tích (hỗ trợ nhiều file)
2. **Chọn ngôn ngữ**: Chọn ngôn ngữ output (hỗ trợ đa ngôn ngữ cùng lúc)
   - Ví dụ: "Tiếng Việt và Tiếng Nhật" → tạo 2 file riêng biệt
3. **Nhận kết quả**: AI agent đọc file schema và tạo báo cáo phân tích chi tiết

#### Ví dụ

```
User: #db-schema-analyst Phân tích file outputs/mydb_schema.md bằng tiếng Việt và tiếng Anh

Agent: Tôi sẽ phân tích file outputs/mydb_schema.md và tạo 2 báo cáo:
       - outputs/analyst_mydb_schema_vi.md (Tiếng Việt)
       - outputs/analyst_mydb_schema_en.md (English)
```

#### Nội dung báo cáo phân tích

Báo cáo bao gồm 11 section:

| # | Section | Nội dung |
|---|---|---|
| 1 | Tổng quan Database | Mục đích, stack công nghệ, quy mô |
| 2 | Phân tích bảng | Nhóm theo nghiệp vụ, vai trò từng bảng |
| 3 | Phân tích Views | Mục đích, bảng nguồn, use case |
| 4 | Phân tích Functions/Procedures | Mục đích, input/output, logic nghiệp vụ |
| 5 | Phân tích Triggers | Bảng, sự kiện kích hoạt, logic xử lý |
| 6 | Phân tích Types | Custom type, giá trị, bảng sử dụng |
| 7 | Phân tích Sequences | Sequence, bảng sở hữu, giá trị |
| 8 | Phân tích Operators | Custom operator, kiểu dữ liệu |
| 9 | Phân tích quan hệ | FK xác định và suy luận |
| 10 | Luồng dữ liệu | Các luồng nghiệp vụ chính |
| 11 | Đặc điểm thiết kế | Pattern, tích hợp, lưu ý |

#### Quy tắc đặt tên file output

```
analyst_[tên file gốc].md           # Nếu chỉ 1 ngôn ngữ
analyst_[tên file gốc]_vi.md        # Tiếng Việt
analyst_[tên file gốc]_en.md        # Tiếng Anh
analyst_[tên file gốc]_ja.md        # Tiếng Nhật
```

File output được đặt cùng thư mục với file schema gốc.

## Cấu trúc Project

```
db_schema_export/
├── __init__.py              # Khởi tạo package
├── __main__.py              # Entry point (python -m)
├── cli.py                   # Phân tích tham số CLI & điều phối
├── env_parser.py            # Parser file .env
├── db_connector.py          # Quản lý kết nối PostgreSQL
├── metadata_collector.py    # Query thu thập metadata schema
├── fk_inference_engine.py   # Suy luận quan hệ FK
├── markdown_generator.py    # Tạo output Markdown
├── ai_analyzer.py           # Phân tích schema bằng AI
├── models.py                # Data model (dataclass)
├── exceptions.py            # Lớp exception tùy chỉnh
├── system_prompt.txt        # System prompt cho AI
├── requirements.txt         # Dependency
└── tests/                   # Bộ test
    ├── conftest.py
    ├── test_cli.py
    ├── test_db_connector.py
    ├── test_exceptions.py
    ├── test_integration.py
    └── test_models.py
```

## Phát triển

### Chạy test

```bash
pytest
```

### Chạy test với coverage

```bash
pytest --cov=db_schema_export --cov-report=term-missing
```

## Mã thoát

| Mã | Ý nghĩa |
|---|---|
| 0 | Thành công (tất cả database đã xử lý) |
| 1 | Lỗi nghiêm trọng (lỗi cấu hình, tất cả database thất bại) |
| 2 | Thành công một phần (một số database thất bại, một số output được tạo) |

## Giấy phép

MIT
