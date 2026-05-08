# DB Schema Export

> 🌐 Language: [English](README.md) | **日本語** | [Tiếng Việt](README.vi.md)

PostgreSQLデータベーススキーマを、ERDダイアグラム、FK推論、およびオプションのAI分析機能を備えた包括的なMarkdownドキュメントにエクスポートします。

## 機能

- **スキーマエクスポート**: データベーススキーマ全体（テーブル、ビュー、関数、トリガー、型、シーケンス、演算子）をMarkdownにエクスポート
- **ERDダイアグラム**: 確認済みおよび推論されたリレーションシップを含むMermaid erDiagramを自動生成
- **ERD画像エクスポート**: mermaid-cliを使用してERDを高解像度PNGとしてレンダリング
- **FK推論エンジン**: 命名規則に基づいて外部キーリレーションシップを自動推論（4段階の信頼度レベル）
- **FKマッピングオーバーライド**: JSONファイルによる手動FKリレーションシップ定義
- **マルチデータベースサポート**: 単一の`.env`ファイルから複数のデータベースを処理
- **マルチスキーマサポート**: 適切なプレフィックス付きで複数のスキーマをエクスポート
- **セクションフィルタリング**: 出力に含めるセクションを選択
- **AI分析**（オプション）: Qwen3-1.7Bを使用してストリーミング出力でスキーマを分析

## インストール

### 要件

- Python >= 3.9
- PostgreSQLデータベース

### ソースからインストール

```bash
pip install -e .
```

### AI分析サポート付きでインストール

```bash
pip install -e ".[ai]"
```

### 開発用依存関係付きでインストール

```bash
pip install -e ".[dev]"
```

## 設定

データベース接続設定を含む`.env`ファイルを作成します：

```env
DB_CONNECTION=pgsql
DB_HOST=localhost
DB_PORT=5432
DB_USERNAME=postgres
DB_PASSWORD=your_password

# 単一データベース
DB_DATABASE=my_database

# または複数データベース（カンマ区切り）
DB_DATABASES=db_one, db_two, db_three
```

両方が定義されている場合、`DB_DATABASES`が`DB_DATABASE`より優先されます。

## 使い方

### 基本的なエクスポート

```bash
db-schema-export
```

### 出力ディレクトリとenvファイルを指定

```bash
db-schema-export --output ./docs --env .env.production
```

### スキーマをフィルタリング

```bash
db-schema-export --schema public,salesforce
```

### セクションをフィルタリング

```bash
db-schema-export --sections erd,tables,views
```

有効なセクション: `erd`, `tables`, `views`, `functions`, `triggers`, `types`, `sequences`, `operators`

### FK推論を無効化

```bash
db-schema-export --no-infer-fk
```

### FKマッピングファイルを使用

```bash
db-schema-export --fk-map ./fk_mappings.json
```

FKマッピングJSONフォーマット：

```json
{
  "order_list.customer_id": "cust_master.cid",
  "public.shift_master.studio_id": "public.studio.stdid"
}
```

### AI分析付きでエクスポート

```bash
db-schema-export --analyze
```

### AI分析を単独で実行

```bash
db-schema-analyze path/to/schema.md
db-schema-analyze path/to/schema.md --output ./analysis
db-schema-analyze path/to/schema.md --model Qwen/Qwen3-1.7B
```

### Pythonモジュールとして実行

```bash
python -m db_schema_export --output ./docs
```

## 出力

各データベースに対して、ツールは以下を生成します：

| ファイル | 説明 |
|---|---|
| `{database}_schema.md` | Markdown形式の完全なスキーマドキュメント |
| `{database}_erd.png` | 高解像度ERDダイアグラム画像（mermaid-cliが必要） |
| `{database}_schema_analysis.md` | AI生成の分析（`--analyze`使用時） |

### スキーマMarkdownの構造

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

## FK推論エンジン

エンジンは4つのマッチングレベルを使用して外部キーリレーションシップを推論します：

| レベル | 信頼度 | 例 |
|---|---|---|
| 完全一致 | 高 | `user_id` → テーブル `user` |
| 複数形一致 | 中 | `user_id` → テーブル `users` |
| サフィックスバリアント | 中 | `store_id` → テーブル `store_master` |
| 短縮名ファジー | 低 | `uid` → テーブル `users` |

推論されたリレーションシップはERDダイアグラムで破線として表示されます。確認済みのFK制約は実線を使用します。

## ERD画像エクスポート

[mermaid-cli](https://github.com/mermaid-js/mermaid-cli)が必要です：

```bash
npm install -g @mermaid-js/mermaid-cli
```

大きなダイアグラムでの可読性のため、画像は4倍スケール（高DPI）でエクスポートされます。

## AI分析

AIアナライザーはQwen3-1.7Bを使用して、以下をカバーする詳細なスキーマ分析レポートを生成します：
- データベースの概要と目的
- テーブルの役割とリレーションシップ
- データフローパターン
- 設計に関する所見

要件：

```bash
pip install transformers torch accelerate
```

モデルは初回実行時に`.cache/`にダウンロードおよびキャッシュされます。

## Kiroスキル

このプロジェクトには、インタラクティブなデータベース分析のための2つのKiroスキルが含まれています。

### db-schema-analyst

エクスポートされたMarkdownスキーマファイルからデータベース構造を分析するスキルです。

#### アクティベーション

Kiroチャットで`#db-schema-analyst`と入力してスキルをコンテキストに読み込み、分析をリクエストします：

```
#db-schema-analyst Analyze the database schema for me
```

#### ワークフロー

1. **ファイル選択**: AIエージェントが分析するMarkdownスキーマファイルの選択を求めます（複数ファイル対応）
2. **言語選択**: 出力言語を選択します（複数言語の同時出力に対応）
   - 例: "Vietnamese and Japanese" → 2つの個別ファイルを生成
3. **結果の受信**: AIエージェントがスキーマファイルを読み取り、詳細な分析レポートを作成します

#### 例

```
User: #db-schema-analyst Analyze outputs/mydb_schema.md in Vietnamese and English

Agent: I will analyze outputs/mydb_schema.md and create 2 reports:
       - outputs/analyst_mydb_schema_vi.md (Vietnamese)
       - outputs/analyst_mydb_schema_en.md (English)
```

#### 分析レポートの内容

レポートには11のセクションが含まれます：

| # | セクション | 内容 |
|---|---|---|
| 1 | データベース概要 | 目的、技術スタック、規模 |
| 2 | テーブル分析 | ビジネスドメイン別にグループ化、各テーブルの役割 |
| 3 | ビュー分析 | 目的、ソーステーブル、ユースケース |
| 4 | 関数/プロシージャ | 目的、入出力、ビジネスロジック |
| 5 | トリガー分析 | テーブル、トリガーイベント、処理ロジック |
| 6 | 型分析 | カスタム型、値、使用方法 |
| 7 | シーケンス分析 | シーケンス、所有テーブル、値 |
| 8 | 演算子分析 | カスタム演算子、データ型 |
| 9 | リレーションシップ分析 | 確認済みおよび推論されたFK |
| 10 | データフロー | 主要なビジネスフロー |
| 11 | 設計ノート | パターン、統合、メモ |

#### 出力ファイルの命名規則

```
analyst_[original_filename].md           # 単一言語
analyst_[original_filename]_vi.md        # ベトナム語
analyst_[original_filename]_en.md        # 英語
analyst_[original_filename]_ja.md        # 日本語
```

出力ファイルはソーススキーマファイルと同じディレクトリに配置されます。

### db-knowledge-graph

データベーススキーマまたは分析ファイルからナレッジグラフ（JSON）を生成するスキルです。

#### アクティベーション

```
#db-knowledge-graph Generate knowledge graph for the database
```

#### ワークフロー

1. **ファイル選択**: スキーマまたは分析Markdownファイルを選択
2. **詳細レベルの選択**: `summary`（テーブル＋リレーションシップのみ）または`detailed`（関数、トリガー、シーケンス、演算子、ビューを含む）
3. **結果の受信**: ノード、エッジ、およびツアー（ビジネスフローのウォークスルー）を含むJSONファイル

#### 出力構造

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

#### ノードタイプ

| タイプ | 説明 |
|---|---|
| `table` | データベーステーブル |
| `view` | データベースビュー |
| `function` | 関数/プロシージャ |
| `trigger` | トリガー |
| `type` | カスタム型 |
| `sequence` | シーケンス |
| `operator` | カスタム演算子 |
| `column` | カラム（PK/FKのみ、詳細モード） |
| `schema` | スキーマ |
| `business_group` | ビジネスドメイングループ |
| `external_system` | 外部統合 |

#### エッジタイプ

| タイプ | 説明 | 重み |
|---|---|---|
| `foreign_key` | 確認済みFK | 1.0 |
| `inferred_fk` | 推論されたFK | 0.6-0.8 |
| `contains` | テーブルがトリガーを含む | 1.0 |
| `calls` | トリガーが関数を呼び出す | 1.0 |
| `belongs_to` | グループ/スキーマに属する | 0.2-0.4 |
| `data_flow` | ビジネスデータフロー | 0.6 |
| `integrates_with` | 外部システム統合 | 0.6 |
| `uses` | テーブルがシーケンスを使用 | 0.2 |
| `depends_on` | ビューがテーブルに依存 | 0.8 |

#### 出力ファイルの命名規則

```
knowledge_graph_[original_filename].json
```

## プロジェクト構造

```
db_schema_export/
├── __init__.py              # パッケージ初期化
├── __main__.py              # エントリーポイント (python -m)
├── cli.py                   # CLI引数解析とオーケストレーション
├── env_parser.py            # .envファイルパーサー
├── db_connector.py          # PostgreSQL接続管理
├── metadata_collector.py    # スキーマメタデータ収集クエリ
├── fk_inference_engine.py   # FKリレーションシップ推論
├── markdown_generator.py    # Markdown出力生成
├── ai_analyzer.py           # AI駆動スキーマ分析
├── models.py                # データモデル（dataclasses）
├── exceptions.py            # カスタム例外クラス
├── system_prompt.txt        # AIシステムプロンプト
├── requirements.txt         # 依存関係
└── tests/                   # テストスイート
    ├── conftest.py
    ├── test_cli.py
    ├── test_db_connector.py
    ├── test_exceptions.py
    ├── test_integration.py
    └── test_models.py
```

## 開発

### テストの実行

```bash
pytest
```

### カバレッジ付きでテストを実行

```bash
pytest --cov=db_schema_export --cov-report=term-missing
```

## 終了コード

| コード | 意味 |
|---|---|
| 0 | 成功（すべてのデータベースが処理済み） |
| 1 | 致命的エラー（設定エラー、すべてのデータベースが失敗） |
| 2 | 部分的成功（一部のデータベースが失敗、一部の出力が生成済み） |

## ライセンス

MIT
