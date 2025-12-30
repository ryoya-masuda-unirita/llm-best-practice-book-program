# Chapter 6 Section 8: AIエージェントのメモリ更新戦略

## 概要

複数のAIエージェントが協調して動作するシステムにおいて、AIエージェント間での記憶やコンテキストの共有は不可欠な要素となります。本プロジェクトは、ファイルベースの共有メモリを安全に扱うための4つの戦略を実装しています。

LLMを用いたAIエージェントは推論に数秒から数十秒を要するため、従来のWebアプリケーションよりも競合状態が発生する可能性が高くなります。本実装では、外部の「ロックマネージャー」を用いた排他制御、およびデータ構造自体を追記型に変更するアプローチを提供します。

## 機能

- **事前ロック（Conservative Lock）**: 処理開始時にファイルのロックを取得し、完了まで保持。最も安全だが占有時間が長い
- **楽観的ロック（Optimistic Lock）**: 読み込み時はロックせず、書き込み直前にバージョン確認とロックを実行。並列性は高いが競合時にやり直しが発生
- **優先度ロック（Preemptible Lock）**: 緊急度の高いエージェントが他者のロックを強制的に剥奪。シャドウコピー機構と併用
- **Immutableメモリ**: 更新を行わず、変更差分を常に新しいタイムスタンプ付きファイルとして保存。ロック不要

## プロジェクト構成

### ディレクトリ構成

```
chapter_6/section_8/
├── src/
│   ├── __init__.py
│   ├── main.py                    # CLIエントリーポイント
│   ├── examples.py                # 各戦略のデモ実装
│   ├── config.py                  # 設定管理
│   ├── logger.py                  # ログ設定
│   ├── client/
│   │   └── llm_client.py          # LLMクライアント
│   └── agent/
│       ├── core/                  # エージェントコア機能
│       └── extensions/
│           └── memory/            # メモリ戦略実装
│               ├── conservative_lock.py   # 事前ロック
│               ├── optimistic_lock.py     # 楽観的ロック
│               ├── preemptible_lock.py    # 優先度ロック
│               ├── immutable_memory.py    # Immutableメモリ
│               ├── lock_manager.py        # ロック管理抽象化
│               └── models.py              # データモデル
├── memory/                        # メモリファイル保存先（実行時生成）
├── pyproject.toml
├── Makefile
└── README.md
```

### アーキテクチャ

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          AI Agent System                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                  │
│  │   Agent A    │  │   Agent B    │  │   Agent C    │                  │
│  │ (priority=50)│  │ (priority=50)│  │(priority=100)│                  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘                  │
│         │                 │                 │                           │
│         └────────────┬────┴─────────────────┘                           │
│                      │                                                  │
│                      ▼                                                  │
│         ┌────────────────────────┐                                      │
│         │    Memory Strategy     │                                      │
│         ├────────────────────────┤                                      │
│         │ ┌────────────────────┐ │                                      │
│         │ │  Conservative Lock │ │  最も安全、長時間ブロック            │
│         │ └────────────────────┘ │                                      │
│         │ ┌────────────────────┐ │                                      │
│         │ │  Optimistic Lock   │ │  高並列性、競合時リトライ            │
│         │ └────────────────────┘ │                                      │
│         │ ┌────────────────────┐ │                                      │
│         │ │  Preemptible Lock  │ │  優先度ベース、緊急対応向け          │
│         │ └────────────────────┘ │                                      │
│         │ ┌────────────────────┐ │                                      │
│         │ │  Immutable Memory  │ │  追記型、ロック不要                  │
│         │ └────────────────────┘ │                                      │
│         └───────────┬────────────┘                                      │
│                     │                                                   │
│                     ▼                                                   │
│         ┌────────────────────────┐                                      │
│         │    Lock Manager        │                                      │
│         │   (LocalDict/Redis)    │                                      │
│         └───────────┬────────────┘                                      │
│                     │                                                   │
│                     ▼                                                   │
│         ┌────────────────────────┐                                      │
│         │   File System / JSON   │                                      │
│         │      (memory/*.json)   │                                      │
│         └────────────────────────┘                                      │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## 使い方

### 環境構成

- **Python**: 3.13.2以上
- **依存ライブラリ**:
  - anthropic>=0.74.1
  - click>=8.3.0
  - google-genai>=1.45.0
  - openai>=2.4.0
  - polars>=1.36.1
  - pydantic>=2.12.2
  - python-dotenv>=1.1.1

### セットアップ

1. **環境変数の設定**

```bash
cp .envrc.example .envrc
# .envrcを編集してAPIキーを設定
export OPENAI_API_KEY="sk-your-openai-api-key-here"
export GEMINI_API_KEY="your-gemini-api-key-here"
```

2. **依存関係のインストール**

```bash
uv sync
```

### 使用方法、実行方法

```bash
# CLIヘルプの表示
python -m src.main --help

# 特定の戦略のデモを実行
python -m src.main --agent example_1_agent_with_conservative_lock
python -m src.main --agent example_2_with_optimistic_lock
python -m src.main --agent example_3_with_preemptive_lock
python -m src.main --agent example_4_with_immutable_memory

# 全ての戦略を順番に実行
python -m src.main --agent all

# メモリ保存先ディレクトリを指定
python -m src.main --agent all --memory-directory ./custom_memory
```

### 出力例

```
=== Example 1: Basic Agent with conservative memory lock ===

====================================================================================================
TIME SERIES LOG: Conservative Lock (Pessimistic)
====================================================================================================
  Time(ms) | Agent                | Event           | Resource             |  Ver | Status  | Details
----------------------------------------------------------------------------------------------------
       0.1 | agent_a              | LOCK_REQUEST    | shared_task_list     |    - | OK      | Requesting exclusive lock
       0.3 | agent_a              | LOCK_ACQUIRED   | shared_task_list     |    - | OK      | Lock acquired successfully
       0.5 | agent_a              | READ            | shared_task_list     |    - | OK      | Read document with 0 entries
     300.8 | agent_a              | PROCESSING      | shared_task_list     |    - | OK      | Simulating LLM inference (300ms)
     301.2 | agent_a              | WRITE           | shared_task_list     |    2 | OK      | Added new task entry
     301.5 | agent_a              | LOCK_RELEASED   | shared_task_list     |    - | OK      | Lock released
     301.8 | agent_b              | LOCK_REQUEST    | shared_task_list     |    - | OK      | Requesting exclusive lock
     302.1 | agent_b              | LOCK_ACQUIRED   | shared_task_list     |    - | OK      | Lock acquired successfully
     302.4 | agent_b              | READ            | shared_task_list     |    - | OK      | Read document with 1 entries
     302.7 | agent_b              | WRITE           | shared_task_list     |    3 | OK      | Marked task as complete
     302.9 | agent_b              | LOCK_RELEASED   | shared_task_list     |    - | OK      | Lock released
====================================================================================================

✓ Agent 'example_1_agent_with_conservative_lock' completed successfully
```

## 戦略の選択基準

| 戦略 | データ整合性 | スループット | 実装複雑度 | 適用場面 |
|------|------------|------------|----------|---------|
| 事前ロック | 高 | 低 | 低 | 複雑な更新、トランザクション |
| 楽観的ロック | 中 | 高 | 中 | 独立した共同編集、低競合率 |
| 優先度ロック | 中 | 中 | 高 | 緊急対応、リアルタイム性要求 |
| Immutableメモリ | 高 | 高 | 中 | 会話履歴、監査ログ |

## 注意点とトレードオフ

- **事前ロック**: 推論時間中に他エージェントがブロックされるため、アクセス頻度が高いリソースでは性能低下に注意
- **楽観的ロック**: LLMの再推論コスト（トークン料金・時間）が発生するため、競合率の監視が重要
- **優先度ロック**: シャドウコピーの管理ポリシー（保存期間、クリーンアップ）を明確に設計
- **Immutableメモリ**: コンパクション処理を怠るとI/Oオーバーヘッドが増大
