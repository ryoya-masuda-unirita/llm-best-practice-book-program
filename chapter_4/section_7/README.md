# Chapter 4 Section 7: イベント駆動型AIエージェント

## 概要

本プロジェクトは、イベント駆動アーキテクチャを採用したAIエージェントシステムの実装例です。ディレクトリを監視し、新しい契約書ファイルが保存されると自動的に契約リスクコンプライアンスパイプラインを起動して、リスク評価レポートを生成します。

イベント駆動アーキテクチャにより、システム内の状態変化やアクションを「イベント」として捉え、それらを契機に各機能が非同期に動作します。これにより、エージェントの各機能を疎結合に保ち、拡張性と応答性に優れたシステムを実現しています。

## 機能

- **ファイル監視**: `watchdog`ライブラリを使用してディレクトリを監視し、新規ファイルを検知
- **イベント駆動処理**: Publish/Subscribe パターンによる疎結合なイベント処理
- **契約書リスク評価**: LangGraphを使用したパイプラインAIエージェントによる自動リスク評価
- **コンプライアンスレポート生成**: 章・条ごとの詳細なリスク分析レポートを自動生成
- **相関ID追跡**: すべてのイベントに相関IDを付与し、処理フローのトレーサビリティを確保

## プロジェクト構成

### ディレクトリ構成

```
chapter_4/section_7/
├── CLAUDE.md                    # プロジェクト設計ドキュメント
├── pyproject.toml               # プロジェクト設定・依存関係
├── data/                        # 契約書ファイル格納ディレクトリ（監視対象）
│   ├── contract_0.md
│   ├── contract_1.md
│   └── ...
├── outputs/                     # 生成されたレポート出力先
└── src/
    ├── __init__.py
    ├── main.py                  # CLI エントリポイント（手動実行用）
    ├── event_runner.py          # イベント駆動ランナー（自動実行用）
    ├── config.py                # 設定
    ├── logger.py                # ロギング設定
    ├── client/
    │   └── llm_client.py        # LLMクライアント定義
    ├── model/
    │   ├── contract_pipeline_model.py  # パイプラインモデル定義
    │   └── event_model.py       # イベントモデル定義
    ├── service/
    │   ├── contract_pipeline_service.py  # パイプラインサービス
    │   └── event_handler.py     # イベントハンドラー
    ├── layer/
    │   └── contract_pipeline/   # パイプラインステージ実装
    │       ├── extraction.py    # 抽出ステージ
    │       ├── risk_scoring.py  # リスク評価ステージ
    │       └── report.py        # レポート生成ステージ
    └── prompt/
        └── contract_pipeline_prompt.py  # プロンプト定義
```

### アーキテクチャ

本システムは、ファイル監視とイベント駆動処理を組み合わせた2層構造で設計されています。

```
┌─────────────────────────────────────────────────────────────────────────┐
│                       Event-Driven AI Agent                              │
│                                                                          │
│  ┌──────────────┐      ┌──────────────┐      ┌────────────────────┐     │
│  │   Watchdog   │─────▶│  Event Bus   │─────▶│  Event Handlers    │     │
│  │ (File Watch) │      │              │      │                    │     │
│  └──────────────┘      └──────────────┘      └────────────────────┘     │
│         │                     │                       │                  │
│         ▼                     ▼                       ▼                  │
│  FileCreatedEvent     Publish/Subscribe       Contract Pipeline         │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘

イベントフロー:
    FileCreatedEvent
          │
          ▼
    ┌─────────────────────┐
    │ FileCreatedHandler  │  (フィルタリング & 変換)
    └──────────┬──────────┘
               │
               ▼
    ContractReviewRequestedEvent
               │
               ▼
    ┌─────────────────────────────┐
    │ ContractReviewHandler       │  (パイプライン実行)
    └──────────┬──────────────────┘
               │
               ▼
    ContractReviewCompletedEvent / ContractReviewFailedEvent

契約書レビューパイプライン:
    ┌─────────────────┐
    │  Input Stage    │  (契約書ファイル読み込み)
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │ Extraction Stage│  (章・条の構造抽出)
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │ Risk Scoring    │  (各条項のリスク評価)
    │     Stage       │
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │ Report Stage    │  (コンプライアンスレポート生成)
    └────────┬────────┘
             │
             ▼
           [END]
```

### 実装の詳細

#### 1. イベントモデル (`src/model/event_model.py`)

システム内で発生するすべての事象をイベントとして定義しています。各イベントには一意のIDと相関IDが付与され、処理フローの追跡を可能にします。

```python
class EventType(StrEnum):
    """Types of events in the system."""
    FILE_CREATED = "file_created"
    CONTRACT_REVIEW_REQUESTED = "contract_review_requested"
    CONTRACT_REVIEW_COMPLETED = "contract_review_completed"
    CONTRACT_REVIEW_FAILED = "contract_review_failed"


@dataclass
class BaseEvent:
    """Base class for all events in the system."""
    event_id: str = field(default_factory=lambda: uuid4().hex)
    correlation_id: str = field(default_factory=lambda: uuid4().hex)
    timestamp: datetime = field(default_factory=datetime.now)
    event_type: EventType = field(default=EventType.FILE_CREATED)
```

**ポイント**: 相関ID（`correlation_id`）により、イベントの連鎖を追跡できます。ファイル検知から最終レポート生成まで、同一の相関IDでログを紐付けられます。

#### 2. イベントハンドラー (`src/service/event_handler.py`)

各イベントタイプに対応するハンドラーを実装。Publish/Subscribe パターンにより、ハンドラーは特定のイベントのみを購読します。

```python
class EventHandler(ABC):
    """Abstract base class for event handlers."""

    @abstractmethod
    def can_handle(self, event: BaseEvent) -> bool:
        """Check if this handler can process the given event."""
        pass

    @abstractmethod
    async def handle(self, event: BaseEvent) -> BaseEvent | None:
        """Process the event and optionally return a new event."""
        pass


class FileCreatedHandler(EventHandler):
    """Handler for FileCreatedEvent."""
    SUPPORTED_EXTENSIONS = {".md", ".txt"}

    def can_handle(self, event: BaseEvent) -> bool:
        return event.event_type == EventType.FILE_CREATED

    async def handle(self, event: BaseEvent) -> ContractReviewRequestedEvent | None:
        # ファイル拡張子チェック後、レビューリクエストイベントを発行
        return ContractReviewRequestedEvent(
            correlation_id=event.correlation_id,
            contract_file_path=event.file_path,
            model=self.model,
            output_directory=self.output_directory,
        )
```

**ポイント**: 各ハンドラーは独立しており、新しい処理を追加する場合は新しいハンドラーを登録するだけで済みます。

#### 3. イベントバス (`src/service/event_handler.py`)

インメモリのイベントバスを実装。本番環境ではKafka、RabbitMQ、AWS EventBridgeなどに置き換え可能です。

```python
class EventBus:
    """Simple in-memory event bus for event-driven architecture."""

    def __init__(self):
        self._handlers: list[EventHandler] = []
        self._callbacks: list[EventCallback] = []

    def register_handler(self, handler: EventHandler) -> None:
        """Register an event handler."""
        self._handlers.append(handler)

    async def publish(self, event: BaseEvent) -> None:
        """Publish an event to the bus."""
        for handler in self._handlers:
            if handler.can_handle(event):
                result_event = await handler.handle(event)
                if result_event:
                    await self.publish(result_event)  # 再帰的にイベントを伝播
```

#### 4. イベント駆動ランナー (`src/event_runner.py`)

`watchdog`ライブラリを使用してディレクトリを監視し、ファイル作成イベントをイベントバスに発行します。

```python
class ContractFileEventHandler(FileSystemEventHandler):
    """Watchdog event handler that bridges file system events to the event bus."""

    SUPPORTED_EXTENSIONS = {".md", ".txt"}
    DEBOUNCE_SECONDS = 1.0  # 重複検知防止

    def on_created(self, event: WatchdogFileCreatedEvent) -> None:
        """Handle file creation events from watchdog."""
        if event.is_directory:
            return

        file_path = str(event.src_path)
        if not self._should_process(file_path):
            return

        file_event = FileCreatedEvent(file_path=file_path)
        asyncio.run_coroutine_threadsafe(
            self.event_bus.publish(file_event),
            self.loop,
        )
```

**ポイント**: デバウンス処理により、同一ファイルに対する連続したイベントを抑制しています。

## 使い方

### 環境構成

- Python: 3.13.2以上
- 主要な依存ライブラリ:
  - `langgraph>=1.0.0` - パイプラインAIエージェント構築
  - `langchain-openai>=1.1.0` - OpenAI連携
  - `watchdog>=6.0.0` - ファイルシステム監視
  - `click>=8.3.0` - CLI構築
  - `pydantic>=2.12.2` - データモデル

### セットアップ

1. 環境変数を設定:

```bash
cp .envrc.example .envrc
# .envrcを編集してAPIキーを設定
```

必要な環境変数:
```
OPENAI_API_KEY=<your_openai_api_key_here>
GEMINI_API_KEY=<your_gemini_api_key_here>
ANTHROPIC_API_KEY=<your_anthropic_api_key_here>
```

2. 依存関係をインストール:

```bash
uv sync
```

### 使用方法、実行方法

#### イベント駆動モード（自動実行）

ディレクトリを監視し、新規ファイルを自動的に処理します:

```bash
# data/ ディレクトリを監視（デフォルト）
uv run python -m src.event_runner

# カスタムディレクトリを監視
uv run python -m src.event_runner -w contracts/

# カスタムモデルを使用
uv run python -m src.event_runner -w data/ -m gpt-4o

# カスタム出力ディレクトリを指定
uv run python -m src.event_runner -w data/ -od reports/
```

CLIオプション:

| オプション | 短縮形 | デフォルト | 説明 |
|-----------|--------|-----------|------|
| `--watch-directory` | `-w` | `data` | 監視するディレクトリ |
| `--model` | `-m` | `gpt-4o-mini` | 使用するLLMモデル |
| `--output-directory` | `-od` | `outputs` | レポート出力先 |

#### 手動実行モード

特定のファイルを直接処理します:

```bash
# 契約書ファイルを指定して実行
uv run python -m src.main -c data/contract_0.md

# カスタムモデルを使用
uv run python -m src.main -c data/contract_0.md -m gpt-4o

# カスタム出力ディレクトリを指定
uv run python -m src.main -c data/contract_0.md -od reports
```

### 出力例

#### イベント駆動モードの実行ログ

```
[2025-12-06 14:30:00] [INFO] EVENT-DRIVEN AI AGENT STARTING
[2025-12-06 14:30:00] [INFO] Watch directory: /path/to/data
[2025-12-06 14:30:00] [INFO] Model: gpt-4o-mini
[2025-12-06 14:30:00] [INFO] Output directory: outputs
[2025-12-06 14:30:00] [INFO] File watcher started. Waiting for new files...
[2025-12-06 14:30:00] [INFO] Press Ctrl+C to stop.

# 新しいファイルが検知された場合:
[2025-12-06 14:31:15] [INFO] New file detected: /path/to/data/contract_new.md
[2025-12-06 14:31:15] [INFO] Event published: file_created [correlation_id=abc12345...]
[2025-12-06 14:31:15] [INFO] Handler FileCreatedHandler processing event
[2025-12-06 14:31:15] [INFO] Event published: contract_review_requested [correlation_id=abc12345...]
[2025-12-06 14:31:15] [INFO] Handler ContractReviewHandler processing event
...
[2025-12-06 14:32:30] [INFO] ============================================================
[2025-12-06 14:32:30] [INFO] CONTRACT REVIEW COMPLETED
[2025-12-06 14:32:30] [INFO]   File: /path/to/data/contract_new.md
[2025-12-06 14:32:30] [INFO]   Report ID: report_12345678
[2025-12-06 14:32:30] [INFO]   Status: needs_review
[2025-12-06 14:32:30] [INFO]   Risk Score: 45/100
[2025-12-06 14:32:30] [INFO]   Report saved to: outputs/compliance_report_12345678.md
[2025-12-06 14:32:30] [INFO] ============================================================
```

#### 生成されるレポート例

```markdown
# 契約書リスクコンプライアンスレポート

**契約書**: ソフトウェア開発業務委託契約書
**レポートID**: report_abc12345
**生成日時**: 2025-12-06T14:32:30

---

## エグゼクティブサマリー

### 総合評価
- **コンプライアンス状態**: ⚠️ 要確認
- **リスクスコア**: 45/100

本契約書は概ね標準的な内容ですが、知的財産権の帰属と
責任制限条項について確認が必要です。

### 主要な懸念事項
- 成果物の著作権帰属が曖昧
- 損害賠償の上限が未設定

### 即時対応が必要な事項
- ⚠️ 第5条の知的財産権条項の明確化
- ⚠️ 第8条の損害賠償上限の設定

---

## セクション別評価詳細

### ⚠️ 第5条（知的財産権）
- **リスクレベル**: 🟠 高
- **コンプライアンス**: 要確認

**検出されたリスク:**

- **成果物の著作権帰属が不明確**
  - カテゴリ: 知的財産権
  - レベル: 🟠 高
  - 推奨対応: 著作権の帰属先を明確に記載する

...
```
