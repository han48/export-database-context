# DB Schema Export — プロジェクト紹介

> 🌐 Language: [English](INTRODUCTION.md) | **日本語** | [Tiếng Việt](INTRODUCTION.vi.md)

## 背景

実際のソフトウェアプロジェクトでは、データベースは長年にわたり複数のチームによって発展していきます。その結果、数百のテーブル、数千のカラム、暗黙的な関係（FK制約なし）、ドメイン固有の命名規則、そして多数の外部システムとの統合を持つ複雑なデータベースシステムが生まれます。

新しい開発者がプロジェクトに参加する際、またはデータベースのレビュー/監査が必要な際、データベース構造全体を理解することは大きな課題となります：

- **最新のドキュメントがない**: スキーマは常に変更されるが、ドキュメントが追いつかない
- **暗黙的な関係**: 多くのFK関係がアプリケーション層にのみ存在し、DB上に制約がない
- **分かりにくい命名規則**: テーブル名/カラム名が省略形やドメイン固有の用語を使用（例：`tenpo` = 店舗、`kessai` = 決済）
- **ERDダイアグラムの欠如**: テーブル間の関係を視覚的に表す図がない
- **多言語対応**: 多国籍チームが複数言語のドキュメントを必要とする

## ソリューション

**DB Schema Export** は、データベース接続 → メタデータ収集 → 関係推論 → ドキュメント生成 → AI分析 → ナレッジグラフ作成までの全プロセスを自動化するツールです。

### 処理パイプライン

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

### 主要コンポーネント

| コンポーネント | 役割 |
|---|---|
| **Schema Export CLI** | PostgreSQLに接続し、メタデータ（テーブル、ビュー、関数、トリガー、型、シーケンス、演算子）を収集し、Markdown + ERDを生成 |
| **FK Inference Engine** | 命名規則からFK関係を推論（4段階の信頼度）、JSONマッピングによるオーバーライドをサポート |
| **ERD Image Export** | Mermaidダイアグラムを高解像度PNGにレンダリング |
| **AI Analyzer** | LLM（Qwen3-1.7B）によるスキーマ分析、ストリーミング出力対応 |
| **Kiro Skills** | 詳細分析とナレッジグラフ生成のための2つのインタラクティブスキル |

## 使用技術

### Core

| 技術 | 目的 |
|---|---|
| Python 3.9+ | メイン言語 |
| psycopg2 | PostgreSQL接続 |
| python-dotenv | .envから設定を読み込み |
| Mermaid | ERDダイアグラム生成 |
| mermaid-cli (mmdc) | ERDをPNGにレンダリング |

### AI & Analysis

| 技術 | 目的 |
|---|---|
| Hugging Face Transformers | LLMのロードと実行 |
| Qwen3-1.7B | スキーマ分析モデル（軽量、ローカル実行） |
| PyTorch | 推論用バックエンド |
| Accelerate | モデルローディングの最適化 |

### Development

| 技術 | 目的 |
|---|---|
| pytest | テスティングフレームワーク |
| pytest-cov | コードカバレッジ |
| hypothesis | プロパティベーステスティング |

### Kiro Integration

| コンポーネント | 目的 |
|---|---|
| Kiro Skills | AIエージェントにインタラクティブ分析を実行させるためのガイド |
| Batch Processing | 大きなファイルをバッチに分割して処理 |
| Knowledge Graph | ビジュアライゼーション用の構造化JSON出力 |

## 使用意義

### 1. 新規開発者のオンボーディング

新しい開発者がプロジェクトに参加する際、コードを読んだり同僚に質問したりして数週間を費やす代わりに、以下のことができます：
- 分析ファイル（analyst_*.md）を読んでデータベースの全体像を理解する
- ERDダイアグラムを見てテーブル間の関係を把握する
- ナレッジグラフの「ツアー」を辿ってビジネスフローを理解する

### 2. コードレビュー & 監査

データベースの変更レビューやセキュリティ監査が必要な場合：
- ツールを実行するたびにドキュメントが自動更新される
- FK推論が開発者が見落とす可能性のある暗黙的な関係を検出する
- ナレッジグラフがデータフローと外部統合ポイントを明確に表示する

### 3. 多言語ドキュメント

多国籍チーム（日本 - ベトナム - 英語）の場合：
- 1つの原語でドキュメントを作成し、その後自動翻訳する
- 技術用語はそのまま保持し、説明部分のみ翻訳する
- すべてのメンバーがデータベースを理解できるようにする

### 4. AI/ツール統合のためのナレッジグラフ

JSONナレッジグラフファイルは以下のツールで使用可能：
- **Visualization tools**: インタラクティブなグラフをレンダリング（D3.js、Cytoscape、Neo4j）
- **AI agents**: コード生成時にLLMにデータベースのコンテキストを提供
- **Documentation platforms**: Confluence、Notion、またはカスタムwikiにインポート
- **Impact analysis**: スキーマ変更時の影響を分析

### 5. 設計上の問題の検出

自動分析により、ツールは以下を検出可能：
- PKのないテーブル
- FK制約のない暗黙的な関係
- 一貫性のない命名規則
- 孤立テーブル（他のテーブルとの関係がない）
- FKカラムのインデックス不足

## FEELCYCLEプロジェクトでの効果

このプロジェクトは、FEELCYCLEフィットネスジムチェーン管理システムの文脈で開発されました — 以下の特徴を持つ複雑なシステムです：

- **3つのデータベース環境**: Development（モバイルアプリ）、Staging、Test
- **100以上のテーブル**: 各staging/testデータベースに存在
- **マルチシステム統合**: Salesforce（CRM）、GMO Payment Gateway（決済）、Heroku Connect（同期）
- **日本語の命名規則**: `tenpo`、`kessai`、`araigae`、`kubun`...
- **多国籍チーム**: ベトナム語と日本語のドキュメントが必要

### 達成された成果

| 出力 | 数量 | 説明 |
|---|---|---|
| Schema Markdown | 3ファイル | 3つのデータベースの完全なドキュメント |
| ERD Diagram | 3ファイル PNG | 視覚的な関係図 |
| 詳細分析 | 6ファイル（3 DB × 2言語） | ベトナム語と日本語による11セクションのレポート |
| Knowledge Graph | 3ファイル JSON | 各ファイル45-128ノード、55-117エッジ、4-5ツアー |

### もたらされた価値

1. **時間の節約**: データベース理解に数週間かかっていたものが数分に短縮
2. **常に最新のドキュメント**: スキーマ変更のたびにツールを再実行
3. **言語の壁を軽減**: 多言語ドキュメントの自動生成
4. **隠れた関係の発見**: FK推論が制約のない関係を発見
5. **AI開発のサポート**: ナレッジグラフがAIエージェントにコンテキストを提供

## 出力構造

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

## 今後の開発方向

- **追加DBMSのサポート**: MySQL、SQL Server、Oracle
- **差分検出**: 2つの時点間のスキーマを比較し、変更をハイライト
- **インタラクティブビジュアライゼーション**: ナレッジグラフをインタラクティブにレンダリングするWeb UI
- **CI/CD統合**: マイグレーション実行時にドキュメントを自動生成
- **スキーマ推奨**: AIによる設計改善の提案（インデックス、制約、正規化）
