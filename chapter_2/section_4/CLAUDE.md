# Chapter 2 Section 4: プロジェクト状態レポート

## プロジェクト概要

このプロジェクトは、**適応的エクスポネンシャルバックオフによるリトライ戦略**を実装したLLM APIリクエストシステムです。本番環境で求められる堅牢性を実現するため、以下の要素を組み合わせています:

- **エクスポネンシャルバックオフ**: 指数関数的に待機時間を増やす再試行(1秒 → 2秒 → 4秒 → ...)
- **ランダムジッター**: サンダリング・ハード問題を回避するための10-50%の揺らぎ
- **インテリジェントなエラー判定**: リトライすべきエラーと即座に失敗すべきエラーの自動分類
- **セマフォによる並行処理制御**: API過負荷を防ぐ同時実行数の制限
- **部分的失敗への対応**: バッチ処理において一部失敗しても継続

## 実装ステータス

### ✅ 完了済み

1. **コア機能**
   - [x] エクスポネンシャルバックオフ計算ロジック
   - [x] ランダムジッター追加機能
   - [x] リトライ可否の判定ロジック(OpenAI/Gemini両対応)
   - [x] Retry-Afterヘッダーのサポート
   - [x] リトライデコレータの実装
   - [x] 非同期バッチ処理機能
   - [x] セマフォによる並行数制御

2. **データモデル**
   - [x] CharacterRequest(個別リクエスト)
   - [x] CharacterRequests(バッチリクエスト)
   - [x] CharacterResponse(レスポンス)
   - [x] YAMLファイルからの読み込み機能

3. **リクエスト定義**
   - [x] 33件の多様なキャラクターリクエスト(YAML形式)
   - [x] 年齢16-78歳、性別バランス、多様な職業設定

4. **テストスイート**
   - [x] 29個の包括的なテストケース
   - [x] リトライロジックのユニットテスト
   - [x] バッチ処理のテスト
   - [x] セマフォ制御の検証
   - [x] エラーハンドリングのテスト

5. **ドキュメント**
   - [x] 詳細なREADME.md
   - [x] pytest設定(pytest.ini)
   - [x] このCLAUDE.md

### 📋 未実装・今後の拡張候補

1. **モニタリング機能**
   - [ ] リトライ回数の統計収集
   - [ ] バックオフ時間の平均・最大値トラッキング
   - [ ] レート制限発生頻度の監視

2. **高度なリトライ戦略**
   - [ ] Circuit Breaker パターンの実装
   - [ ] Adaptive rate limiting(動的レート調整)
   - [ ] Per-endpoint rate limiting

3. **最適化**
   - [ ] バックオフパラメータの自動チューニング
   - [ ] リクエスト優先度の実装
   - [ ] キャッシュ機構の統合

## コードアーキテクチャ

### 核心的な実装: `src/service/request_llm.py`

このファイルには、プロジェクトの中心となるリトライロジックとバッチ処理が実装されています。

#### 1. バックオフ計算(30-39行目)

```python
def calculate_backoff_with_jitter(attempt: int, base: float = BASE_BACKOFF_SECONDS) -> float:
    """エクスポネンシャルバックオフ時間をランダムジッターと共に計算"""
    backoff = min(base * (2 ** attempt), MAX_BACKOFF_SECONDS)
    jitter_range = backoff * (JITTER_MAX - JITTER_MIN)
    jitter = random.uniform(backoff * JITTER_MIN, backoff * JITTER_MIN + jitter_range)
    return backoff + jitter
```

**設計判断**:
- `2^attempt`による指数関数的増加で、初期は短く後半は長い待機時間
- `MAX_BACKOFF_SECONDS=60`で無限増加を防止
- `10-50%`のジッターで複数クライアントの再試行を分散

**調整ポイント**:
- `BASE_BACKOFF_SECONDS`: 初期待機時間(デフォルト1秒)
- `MAX_BACKOFF_SECONDS`: 最大待機時間(デフォルト60秒)
- `JITTER_MIN/MAX`: ジッターの範囲(デフォルト10-50%)

#### 2. エラー判定(42-85行目)

```python
def should_retry_error(error: Exception) -> tuple[bool, int | None]:
    """エラーがリトライ可能か判定し、Retry-After値を抽出"""
```

**判定ロジック**:

| エラー種別 | リトライ | 理由 |
|-----------|---------|------|
| `RateLimitError` (429) | ✅ Yes | 一時的なレート制限、Retry-After優先 |
| `APITimeoutError` | ✅ Yes | ネットワーク遅延の可能性 |
| `APIConnectionError` | ✅ Yes | 一時的な接続問題 |
| `APIError` (500, 502, 503, 504) | ✅ Yes | サーバー側の一時的障害 |
| `APIError` (400, 401) | ❌ No | リクエスト自体の問題 |
| `google_exceptions.ResourceExhausted` | ✅ Yes | Geminiのクォータ超過 |
| `google_exceptions.ServiceUnavailable` | ✅ Yes | Geminiサービス一時停止 |
| その他 | ❌ No | 未知のエラーは安全側に倒す |

**重要な実装詳細**:
- Retry-Afterヘッダーが存在する場合、それを優先使用
- エラーの`status_code`属性で詳細な判定
- 型チェック(`isinstance`)でエラー種別を厳密に確認

#### 3. リトライデコレータ(88-130行目)

```python
@retry_with_exponential_backoff(max_retries=5)
async def request_openai(...):
    # リトライロジックが自動適用される
```

**動作フロー**:
1. 関数実行を試行
2. エラー発生時、`should_retry_error()`で判定
3. リトライ可能なら`calculate_backoff_with_jitter()`で待機
4. `asyncio.sleep(backoff_time)`で待機
5. 再試行(最大`max_retries`回)
6. 成功または最大試行回数到達で終了

**ログ出力**:
- リトライ時: `[WARNING] Request failed (attempt X/Y). Error: ... Retrying in Z.XXs...`
- Retry-After時: `[WARNING] Rate limit hit (attempt X/Y). Retry-After: Zs. Waiting...`
- 最終失敗: `[ERROR] Request failed after X attempts. Error: ...`

#### 4. バッチ処理(204-265, 268-329行目)

```python
async def batch_request_openai(
    character_requests: list[CharacterRequest],
    parallelism: int = 5,
):
    semaphore = asyncio.Semaphore(parallelism)

    async def request_with_semaphore(req):
        async with semaphore:
            return await request_openai(...)

    tasks = [request_with_semaphore(req) for req in character_requests]
    results = await asyncio.gather(*tasks, return_exceptions=True)
```

**設計のポイント**:
- `asyncio.Semaphore(parallelism)`: 同時実行数を制限
- `asyncio.gather(..., return_exceptions=True)`: 一部失敗しても全体は継続
- 成功/失敗を分離して、成功したもののみ返却
- 詳細な統計情報をログ出力

**並行数の推奨値**:
- 開発/テスト: `parallelism=2-3`(安全)
- 通常運用: `parallelism=5-10`(標準)
- 高速処理: `parallelism=10-20`(レート制限に注意)

### メインエントリーポイント: `src/main.py`

#### CLIインターフェース(26-77行目)

```python
@click.command()
@click.option("--request-file", "-rf", required=True)
@click.option("--llm-provider", "-lp", type=click.Choice(LLMProvider), required=True)
@click.option("--model", "-m", required=True)
@click.option("--parallelism", "-p", type=int, default=5)
```

**パラメータ設計**:
- 必須パラメータ: `request-file`, `llm-provider`, `model`
- オプション: `parallelism`(デフォルト5), `output-directory`, `user-id`, `storage-type`
- 短縮形を提供してコマンド入力を簡素化

#### バッチ処理オーケストレーション(92-136行目)

**実行フロー**:
1. YAMLファイルからリクエストを読み込み(`CharacterRequests.load_from_yaml()`)
2. LLMOpsロガーを初期化
3. プロバイダーに応じてバッチ処理関数を呼び出し
4. 結果を個別のJSONファイルに保存(`{provider}_{index:03d}_{uuid}.json`)
5. 統計情報をログ出力

### データモデル: `src/model/model.py`

#### CharacterRequests(25-41行目)

```python
class CharacterRequests(BaseModel):
    requests: list[CharacterRequest]

    @staticmethod
    def load_from_yaml(file_path: str) -> "CharacterRequests":
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return CharacterRequests.model_validate(data)
```

**重要な機能**:
- YAMLファイルからの直接読み込み
- Pydanticによる自動バリデーション
- 型安全なデータ構造

### リクエスト定義: `character_requests.yaml`

**構造**:
```yaml
requests:
  - gender: female
    age: 25
    additional_instructions: "..."
  - gender: male
    age: 30
    additional_instructions: "..."
  # ... 全33件
```

**多様性の確保**:
- 年齢: 16-78歳(若者、中年、高齢者をカバー)
- 性別: バランスの取れた分布
- 職業: 弓使い、騎士、魔法使い、盗賊、僧侶、商人、画家、暗殺者、王子、預言者、鍛冶職人、舞踏家、探偵、錬金術師、侍、漁師、ジャーナリスト、義賊、図書館司書、長老、曲芸師、スパイ、番人等

## テスト戦略

### テストファイル: `tests/test_request_llm.py`

29個のテストケースを7つのクラスに分類:

#### 1. TestCalculateBackoffWithJitter(4テスト)

**目的**: バックオフ計算ロジックの検証

```python
def test_exponential_growth(self):
    # 指数関数的増加を確認
    backoff_0 = calculate_backoff_with_jitter(0)  # ~1.1-1.5秒
    backoff_1 = calculate_backoff_with_jitter(1)  # ~2.2-3.0秒
    backoff_2 = calculate_backoff_with_jitter(2)  # ~4.4-6.0秒
```

**テストポイント**:
- 指数関数的増加の確認
- 最大値の制限(60秒)
- ジッターのランダム性
- カスタムベース時間

#### 2. TestShouldRetryError(10テスト)

**目的**: エラー判定ロジックの検証

**カバー範囲**:
- ✅ `RateLimitError`(Retry-Afterあり/なし)
- ✅ `APITimeoutError`
- ✅ `APIConnectionError`
- ✅ `APIError`(500, 400, 401等)
- ✅ Google Geminiエラー(`ResourceExhausted`, `ServiceUnavailable`)
- ✅ 未知のエラー

#### 3. TestRetryWithExponentialBackoff(5テスト)

**目的**: デコレータの動作検証

```python
@pytest.mark.asyncio
async def test_success_after_retries(self):
    # 2回失敗した後、3回目で成功
    call_count = 0

    @retry_with_exponential_backoff(max_retries=3)
    async def mock_function():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise APITimeoutError("Timeout")
        return "success"
```

**テストポイント**:
- 初回成功時の動作
- リトライ後の成功
- 最大リトライ回数超過
- リトライ不可エラーの即時失敗
- Retry-Afterヘッダーの尊重

#### 4-5. TestRequestOpenAI/TestRequestGemini(各2テスト)

**目的**: 個別リクエスト関数の検証

**モッキング戦略**:
- `openai_client.beta.chat.completions.parse`をAsyncMockで置換
- `google_genai_client.aio.models.generate_content`をAsyncMockで置換
- レスポンスオブジェクトを手動構築

#### 6-7. TestBatchRequestOpenAI/TestBatchRequestGemini(各3テスト)

**目的**: バッチ処理とセマフォの検証

```python
async def test_batch_respects_parallelism(self):
    concurrent_calls = 0
    max_concurrent_calls = 0

    async def mock_parse(*args, **kwargs):
        nonlocal concurrent_calls, max_concurrent_calls
        concurrent_calls += 1
        max_concurrent_calls = max(max_concurrent_calls, concurrent_calls)
        await asyncio.sleep(0.1)
        concurrent_calls -= 1
        return mock_result

    # max_concurrent_calls <= parallelism を確認
    assert max_concurrent_calls <= 2
```

**テストポイント**:
- 全リクエスト成功
- 部分的失敗のハンドリング(一部失敗しても継続)
- セマフォによる並行数制御

### テスト実行

```bash
# 全テスト実行
pytest tests/test_request_llm.py -v

# 特定クラスのみ
pytest tests/test_request_llm.py::TestRetryWithExponentialBackoff -v

# カバレッジレポート
pytest tests/test_request_llm.py --cov=src/service/request_llm --cov-report=html
```

**期待される結果**: 全29テストがパス(✅)

## 使用パターン

### パターン1: 標準的なバッチ処理

```bash
python -m src.main \
  -rf character_requests.yaml \
  -lp gemini \
  -m gemini-2.5-flash \
  -p 5 \
  -od outputs
```

**適用ケース**:
- 夜間バッチでの大量処理
- 定期的なキャラクター生成
- 中程度の並行数で安定した処理

### パターン2: 安全優先(低速)

```bash
python -m src.main \
  -rf character_requests.yaml \
  -lp openai \
  -m gpt-4o-mini \
  -p 2 \
  -od outputs
```

**適用ケース**:
- レート制限が厳しいAPI
- 初回テスト実行
- 課金コスト削減優先

### パターン3: 高速処理(リスク有)

```bash
python -m src.main \
  -rf character_requests.yaml \
  -lp gemini \
  -m gemini-2.5-flash \
  -p 15 \
  -od outputs
```

**適用ケース**:
- 緊急の大量処理
- レート制限に余裕がある環境
- リトライ前提で高速化優先

**注意**: レート制限エラーが頻発する可能性あり

## 開発ガイドライン

### リトライパラメータの調整

`src/service/request_llm.py`の定数を変更:

```python
MAX_RETRIES = 5              # 最大リトライ回数(デフォルト: 5)
MAX_BACKOFF_SECONDS = 60     # 最大待機時間(デフォルト: 60秒)
BASE_BACKOFF_SECONDS = 1     # 初期待機時間(デフォルト: 1秒)
JITTER_MIN = 0.1             # ジッター最小(デフォルト: 10%)
JITTER_MAX = 0.5             # ジッター最大(デフォルト: 50%)
```

**調整例**:
- より積極的なリトライ: `MAX_RETRIES = 10, MAX_BACKOFF_SECONDS = 120`
- より慎重なリトライ: `MAX_RETRIES = 3, BASE_BACKOFF_SECONDS = 2`

### 新しいエラータイプの追加

`should_retry_error()`関数に追加:

```python
def should_retry_error(error: Exception) -> tuple[bool, int | None]:
    # 既存のチェック...

    # 新しいエラータイプ
    if isinstance(error, CustomAPIError):
        if error.is_retryable:
            return True, None
        return False, None
```

**テストの追加も忘れずに**:

```python
def test_custom_error(self):
    error = CustomAPIError(is_retryable=True)
    should_retry, retry_after = should_retry_error(error)
    assert should_retry is True
```

### 新しいLLMプロバイダーの追加

1. **モデルEnum追加** (`src/client/llm_client.py`):

```python
class NewProviderModel(StrEnum):
    MODEL_1 = "model-1"
    MODEL_2 = "model-2"
```

2. **リクエスト関数実装** (`src/service/request_llm.py`):

```python
@retry_with_exponential_backoff()
async def request_new_provider(
    character_request: CharacterRequest,
    model: NewProviderModel,
    llmops_logger: LLMOpsLogger,
    user_id: str = "default_user",
) -> CharacterResponse:
    # 実装
```

3. **バッチ処理関数実装**:

```python
async def batch_request_new_provider(...):
    # batch_request_openai()をテンプレートに実装
```

4. **main.pyに統合**:

```python
elif llm_provider == LLMProvider.NEW_PROVIDER:
    results = await batch_request_new_provider(...)
```

5. **テストの追加** (`tests/test_request_llm.py`):

```python
class TestRequestNewProvider:
    @pytest.mark.asyncio
    async def test_successful_request(self, ...):
        # テスト実装
```

## パフォーマンス考察

### 処理時間の見積もり

**33リクエストの処理時間**:

| 並行数 | エラーなし | 一部リトライ | レート制限多発 |
|--------|-----------|-------------|---------------|
| 2 | ~25-40秒 | ~40-60秒 | ~80-120秒 |
| 5 | ~12-20秒 | ~20-35秒 | ~50-90秒 |
| 10 | ~8-15秒 | ~15-30秒 | ~40-80秒 |

**前提**:
- 1リクエストあたり平均1.5-3秒(API処理時間)
- リトライ時の待機時間: 1回目1-2秒、2回目2-4秒
- レート制限時: Retry-Afterに従う(通常3-10秒)

### メモリ使用量

- 基本メモリ: ~50-100MB(Python環境)
- 1リクエストあたり: ~1-2MB(プロンプト + レスポンス)
- 33リクエスト同時: ~150-200MB(十分実行可能)

### ボトルネック

1. **API応答時間**: 最大の要因
2. **ネットワーク遅延**: 地理的距離による影響
3. **レート制限**: プロバイダーの制約
4. **リトライ待機時間**: エラー頻発時に増大

## トラブルシューティング

### 問題1: レート制限エラーが頻発

**症状**:
```
[WARNING] Rate limit hit (attempt 1/6). Retry-After: 10s. Waiting...
```

**解決策**:
1. 並行数を減らす: `-p 2` または `-p 3`
2. リクエスト数を減らす(YAMLファイルを分割)
3. より高いプランのAPIキーを使用

### 問題2: タイムアウトが多発

**症状**:
```
[WARNING] Request failed (attempt 1/6). Error: APITimeoutError: Request timed out.
```

**解決策**:
1. `MAX_RETRIES`を増やす(5 → 10)
2. `MAX_BACKOFF_SECONDS`を増やす(60 → 120)
3. ネットワーク接続を確認
4. プロキシ設定を確認

### 問題3: 特定のリクエストが常に失敗

**症状**:
```
[ERROR] Request 12 failed: APIError: Bad request
[WARNING] Failed request indices: [12]
```

**解決策**:
1. 該当インデックスの`additional_instructions`を確認
2. プロンプトが長すぎる場合は短縮
3. 不適切な内容がないか確認
4. 手動で該当リクエストを修正

### 問題4: テストが失敗

**症状**:
```
FAILED tests/test_request_llm.py::TestXXX::test_xxx
```

**解決策**:
1. 依存関係を確認: `uv sync --all-extras`
2. Pythonバージョン確認: 3.13.2以上
3. 詳細ログ確認: `pytest -vv --tb=long`
4. 特定のテストのみ実行: `pytest tests/test_request_llm.py::TestXXX -v`

## ベストプラクティス

### 1. リトライパラメータの選択

**開発環境**:
```python
MAX_RETRIES = 3
MAX_BACKOFF_SECONDS = 30
```
理由: 早く失敗してデバッグしやすい

**本番環境**:
```python
MAX_RETRIES = 5-7
MAX_BACKOFF_SECONDS = 60-120
```
理由: 一時的な障害からの自動復旧を優先

### 2. 並行数の設定

**推奨フロー**:
1. `parallelism=2`で動作確認
2. エラーなければ`parallelism=5`に増やす
3. レート制限が出なければ`parallelism=10`
4. レート制限が出たら前の値に戻す

### 3. エラーログの監視

**重要なログパターン**:
- `Rate limit hit`: レート制限の兆候、並行数を減らす検討
- `Request failed after X attempts`: 永続的な問題の可能性
- `Failed request indices: [...]`: 特定リクエストの問題

### 4. テストの追加

**新機能追加時**:
1. 正常系テスト(成功ケース)
2. 異常系テスト(エラーケース)
3. リトライ動作のテスト
4. エッジケースのテスト

## 既知の制限事項

1. **リトライ回数の上限**: 現在5回固定(デコレータ内で変更可能)
2. **Retry-Afterの最大値**: 無制限(非常に長い値が返される可能性)
3. **部分失敗時の再実行**: 失敗したリクエストのみの再実行機能なし
4. **優先度制御**: リクエストの優先度付け機能なし
5. **永続化**: 中断時の再開機能なし

## 今後の改善案

### 短期(すぐ実装可能)

1. **リトライ統計の収集**:
   - 総リトライ回数
   - リトライ成功率
   - 平均バックオフ時間

2. **設定ファイル化**:
   - リトライパラメータを外部設定ファイルに移動
   - 環境ごとの設定切り替え

3. **失敗リクエストの保存**:
   - 失敗したリクエストを別ファイルに保存
   - 再実行用のYAMLを自動生成

### 中期(設計変更必要)

1. **Circuit Breaker パターン**:
   - 連続失敗時に一定時間リクエスト停止
   - 復旧後に自動再開

2. **Adaptive rate limiting**:
   - エラー率に応じて並行数を自動調整
   - 成功率が高い場合は並行数を増やす

3. **チェックポイント機能**:
   - 処理途中で中断しても再開可能
   - 処理済みリクエストをスキップ

### 長期(大規模リファクタリング)

1. **分散処理対応**:
   - 複数ワーカーでの並列処理
   - Redis等を使った状態管理

2. **リアルタイムモニタリング**:
   - Prometheus/Grafanaとの統合
   - アラート機能

3. **Machine Learning統合**:
   - 過去のエラーパターンから最適なリトライ戦略を学習
   - 動的なバックオフパラメータ調整

## まとめ

このプロジェクトは、本番環境で求められる堅牢なLLM APIリクエストシステムの実装例です。エクスポネンシャルバックオフ、ランダムジッター、インテリジェントなエラー判定、セマフォによる並行制御を組み合わせることで、一時的な障害に対する自動復旧とシステム全体の安定性を実現しています。

29個の包括的なテストケースにより、リトライロジックの正しさが保証されており、実際のプロダクション環境での使用にも耐えうる品質となっています。

このコードベースは、LLM APIを使用する他のプロジェクトのリファレンス実装として活用できます。
