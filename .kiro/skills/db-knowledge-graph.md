# Database Knowledge Graph Generator

Bạn là chuyên gia tạo knowledge graph từ nội dung phân tích database. Khi skill này được kích hoạt, hãy thực hiện theo quy trình sau:

## Quy trình thực hiện

### Bước 1: Hỏi người dùng

Hỏi người dùng:

1. **File phân tích nguồn**: File markdown phân tích database (analyst_*.md) hoặc file schema gốc (*_schema.md) cần tạo knowledge graph.
2. **Mức độ chi tiết**: 
   - `summary`: Chỉ bảng và quan hệ chính (phù hợp cho overview)
   - `detailed`: Bao gồm cả cột, function, trigger, view, sequence, operator (phù hợp cho phân tích sâu)
   - Mặc định: `detailed`

### Bước 2: Đọc và trích xuất thông tin

Đọc file phân tích/schema và trích xuất:
- Bảng và vai trò
- Views và định nghĩa SQL
- Functions/Procedures và mục đích
- Triggers và logic
- Types tùy chỉnh
- Sequences
- Operators
- Quan hệ giữa các bảng (FK xác nhận và suy luận)
- Cột quan trọng (PK, FK)
- Nhóm nghiệp vụ
- Luồng dữ liệu

### Bước 3: Tạo knowledge graph theo batch

**QUAN TRỌNG - Viết JSON theo batch vì file output có thể rất lớn:**

1. Tạo folder tạm `tmp/` cùng thư mục với file nguồn
2. Viết từng phần vào file riêng trong folder `tmp/`:
   - `tmp/01_metadata.json` — Object `version` + `project`
   - `tmp/02_nodes_schemas.json` — Nodes loại schema + business_group + external_system
   - `tmp/03_nodes_tables.json` — Nodes loại table (tất cả bảng)
   - `tmp/04_nodes_functions.json` — Nodes loại function (nếu detailed)
   - `tmp/05_nodes_triggers.json` — Nodes loại trigger (nếu detailed)
   - `tmp/06_nodes_sequences.json` — Nodes loại sequence (nếu detailed)
   - `tmp/07_nodes_operators.json` — Nodes loại operator (nếu detailed)
   - `tmp/08_edges_fk.json` — Edges loại foreign_key + inferred_fk
   - `tmp/09_edges_belongs.json` — Edges loại belongs_to
   - `tmp/10_edges_triggers.json` — Edges loại contains + calls (trigger-related)
   - `tmp/11_edges_flow.json` — Edges loại data_flow + integrates_with + uses
   - `tmp/12_tour.json` — Array tour
3. Sau khi viết xong tất cả batch, merge thành file JSON output cuối cùng
4. Xóa folder `tmp/`

**Lợi ích**: Tránh mất dữ liệu khi file quá lớn, dễ kiểm tra từng phần, có thể retry từng batch nếu lỗi.

### Bước 4: Validate JSON

Sau khi merge, thực hiện validation trực tiếp (KHÔNG dùng script bên ngoài):

1. **Đọc lại file JSON output** và kiểm tra:
   - JSON parse thành công (valid syntax)
   - Có đủ các key: `version`, `project`, `nodes`, `edges`, `tour`
   - `nodes` là array, `edges` là array, `tour` là array
2. **Kiểm tra tham chiếu edge**: Với mỗi edge, kiểm tra `source` và `target` đều tồn tại trong danh sách node IDs
3. **Kiểm tra tham chiếu tour**: Với mỗi tour item, kiểm tra tất cả `nodeIds` đều tồn tại trong danh sách node IDs
4. **Báo cáo kết quả**: In ra số nodes, edges, tours và danh sách lỗi (nếu có)
5. **Sửa lỗi**: Nếu có lỗi tham chiếu, sửa trực tiếp trong file output (xóa edge/tour reference lỗi hoặc thêm node thiếu)

### Bước 5: Tạo file output cuối cùng

Format tên: `knowledge_graph_[tên file gốc không có extension].json`

Đặt file output cùng thư mục với file nguồn.

## Cấu trúc JSON output

```json
{
  "version": "1.0.0",
  "project": {
    "name": "tên database",
    "description": "mô tả ngắn về database",
    "analyzedAt": "ISO 8601 timestamp",
    "source": "tên file nguồn"
  },
  "nodes": [],
  "edges": [],
  "tour": []
}
```

### Định nghĩa Node

Mỗi node đại diện cho một entity trong database:

```json
{
  "id": "type:schema.name",
  "type": "loại node",
  "name": "tên hiển thị",
  "summary": "mô tả chi tiết (comment từ DB + giải thích AI)",
  "tags": ["tag1", "tag2"],
  "complexity": "simple | moderate | complex"
}
```

**Quy tắc cho trường `summary`:**
- Nếu object có comment trong database schema, đặt comment đó lên đầu
- Thêm giải thích bổ sung của AI Agent
- Nếu không có comment từ database, chỉ ghi giải thích của AI Agent

**Quy tắc cho trường `complexity`:**
- `simple`: Bảng ít cột (<10), function đơn giản, sequence cơ bản
- `moderate`: Bảng trung bình (10-30 cột), function có logic nghiệp vụ
- `complex`: Bảng nhiều cột (>30), bảng trung tâm có nhiều quan hệ, function phức tạp

#### Các loại node (type)

| Type | Mô tả | Khi nào tạo |
|---|---|---|
| `table` | Bảng database | Luôn luôn |
| `view` | View | Khi có view |
| `function` | Function/Procedure | Chế độ detailed |
| `trigger` | Trigger | Chế độ detailed |
| `type` | Custom type | Khi có custom type |
| `sequence` | Sequence | Chế độ detailed |
| `operator` | Custom operator | Chế độ detailed |
| `column` | Cột (chỉ PK/FK) | Chế độ detailed |
| `schema` | Schema | Khi có nhiều schema |
| `business_group` | Nhóm nghiệp vụ | Luôn luôn |
| `external_system` | Hệ thống bên ngoài | Khi có tích hợp |

### Định nghĩa Edge

```json
{
  "source": "node_id nguồn",
  "target": "node_id đích",
  "type": "loại quan hệ",
  "direction": "forward | backward | bidirectional",
  "weight": 0.0-1.0,
  "label": "mô tả ngắn (tùy chọn)"
}
```

**Quy tắc weight:**
- `1.0`: Quan hệ bắt buộc (confirmed FK, contains, calls)
- `0.8`: Suy luận tin cậy cao
- `0.6`: Suy luận trung bình hoặc data flow
- `0.4`: belongs_to_group
- `0.2`: belongs_to_schema, uses_sequence

#### Các loại edge

| Type | Mô tả | Weight |
|---|---|---|
| `foreign_key` | FK xác nhận | 1.0 |
| `inferred_fk` | FK suy luận | 0.6-0.8 |
| `contains` | Bảng chứa trigger | 1.0 |
| `calls` | Trigger gọi function | 1.0 |
| `belongs_to` | Thuộc group/schema | 0.2-0.4 |
| `data_flow` | Luồng dữ liệu | 0.6 |
| `integrates_with` | Tích hợp bên ngoài | 0.6 |
| `uses` | Bảng dùng sequence | 0.2 |
| `depends_on` | View phụ thuộc table | 0.8 |

### Định nghĩa Tour

```json
{
  "order": 1,
  "title": "Tên luồng nghiệp vụ",
  "description": "Mô tả chi tiết luồng: bắt đầu từ đâu, qua bảng nào, kết thúc ở đâu.",
  "nodeIds": ["table:public.cust_master", "table:public.cust_store"]
}
```

Nên tạo 3-5 tour cho các luồng nghiệp vụ chính.

## Quy tắc tạo ID

Format: `{type}:{schema}.{name}`

- Table: `table:public.cust_master`
- View: `view:public.active_members`
- Function: `function:public.calculate_with_tax`
- Trigger: `trigger:salesforce.trg_cust_memtype_updates`
- Sequence: `sequence:public.cust_master_cid_seq`
- Operator: `operator:public.->_text`
- Column: `column:public.cust_master.cid`
- Schema: `schema:public`
- Business group: `group:member_management`
- External system: `external:salesforce`

## Quy tắc chung

- ID phải unique
- Ưu tiên trích xuất từ dữ liệu thực tế trong file, không bịa đặt
- Với chế độ `summary`: chỉ tạo node loại `table`, `business_group`, `schema`, `external_system` và edge loại `foreign_key`, `inferred_fk`, `belongs_to`, `data_flow`
- Với chế độ `detailed`: tạo TẤT CẢ loại node bao gồm `view`, `function`, `trigger`, `type`, `sequence`, `operator`
- Nếu file nguồn không có thông tin cho một loại node/edge, bỏ qua
- JSON phải valid và được format đẹp (indented 2 spaces)
- Đảm bảo mọi edge và tour tham chiếu đến node_id tồn tại
