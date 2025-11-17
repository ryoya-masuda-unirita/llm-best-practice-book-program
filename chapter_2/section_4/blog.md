# 第4項　LLMリクエストの適応的バックオフによるリトライ

## 概要
前項（第2章第3項）では、LLMリクエストにおけるタイムアウト設定とフォールバック戦略について解説しました。本項では、さらに一歩進んで、LLM APIへのリクエストが失敗した際の再試行（リトライ）に関する適応的バックオフ戦略について説明します。

LLM APIへのリクエストが失敗した際に、単純に即座に再試行するのではなく、失敗回数に応じて待機時間を段階的に伸ばしながら再試行する「適応的バックオフ戦略」は、堅牢なシステムを構築するための重要な設計プラクティスです。このアプローチは、固定間隔のリトライとは異なり、指数関数的に待機時間を調整することで、API側への負荷集中や連続失敗を効果的に抑制します。一時的なネットワーク障害やレート制限エラーに対して自動的に復旧を図りつつ、過剰なリトライが引き起こすシステムへの悪影響を防ぎます。特に高頻度に同時にLLM APIを呼び出すシステムにおいて、信頼性と復元力を大幅に向上させる実用的なアプローチです。

## 解決したい課題
LLMを活用したシステム開発において、Web APIとして提供されるLLM APIとの通信の信頼性確保は避けて通れない課題です。最も頻繁に発生する問題の一つが、一時的なレート制限エラー（HTTP 429）でしょう。例えば、AIエージェントで大量の文書を処理する際、LLM APIに対して短時間で数百件のリクエストを送信した結果、レート制限に抵触して処理が中断されてしまうケースが考えられます。このような状況で単純に即時リトライを実装すると、レート制限がリセットされる前に再度リクエストを送り続け、最終的にはアクセスが長時間制限される事態を招きかねません。

もう一つの深刻な課題は、障害発生時の再試行リクエストが集中することでシステム全体が過負荷に陥る「サンダリング・ハード問題」です。たとえば大規模なチャットボットシステムにおいて、LLMプロバイダー側で一時的な障害が発生した際、数千のクライアントが一斉にリトライを実行した結果、APIサーバーが完全にダウンし、サービス復旧が大幅に遅れたという事態も想定されます。もちろん高負荷が予想されるWebサービスではインフラの自動スケーリングや負荷分散等の対策は取られているでしょうが、すべてのインシデントを回避することは不可能です。このような状況では、単純なリトライ機能は逆効果となり、システム全体の可用性を著しく低下させてしまうでしょう。

## 解決策の提案
これらの課題を解決するため、指数関数的に遅延時間を伸ばしながら再試行する「エクスポネンシャルバックオフ」に「ランダムジッター」を組み合わせた適応的バックオフ戦略を導入します。具体的な実装として、最初のリトライは1秒後、次は2秒後、4秒後、8秒後というように待機時間を倍増させます。さらに、計算された各待機時間に10%から50%程度のランダムな揺らぎ（ジッター）を加えることで、複数のクライアントからのリクエストが完全に同じタイミングで実行されるのを防ぎ、負荷を分散させます。

エラーの種類に応じた分岐ロジックも極めて重要です。レート制限エラー（HTTP 429）の場合、レスポンスヘッダーに含まれる Retry-After の値を最優先で利用し、APIサーバー側の指示に従うべきです。一方で、認証エラー（HTTP 401）や不正なリクエスト（HTTP 400）のような、リトライしても成功の見込みがない恒久的なエラーに対しては、再試行せずに即座に処理を中断し、定義されたフォールバック処理へ移行します。これにより、無駄なリトライを排除し、効率的なエラーハンドリングを実現します。

## 適用するユースケース
このプラクティスは、高頻度でLLM APIを呼び出すチャットボットや対話システムにおいて特に効果を発揮します。例えば、ECサイトのカスタマーサポート用チャットボットでは、セール期間中に複数のユーザーから同時に問い合わせが殺到し、短時間で大量のAPIリクエストが発生します。適応的バックオフを導入することで、一時的なレート制限エラーが発生しても、システムが自動的に復旧し、ユーザーへの応答を途切れることなく継続できます。

大量のデータを扱うバッチ処理やデータ分析システムにおいても、このプラクティスの適用は有効です。例えば、数千件のニュース記事を夜間に要約するバッチジョブを考えます。処理の途中でAPIのレート制限に達することは頻繁に起こり得ますが、適応的バックオフを用いることで、処理を完全に中断することなく、最後まで着実に実行できます。特に処理時間に比較的余裕がある夜間バッチなどでは、長めのバックオフ時間を設定することで、より確実な処理完了を保証できます。

## 導入のポイント
このプラクティスを効果的に導入するには、まずリトライ対象とするエラーコードを明確に定義することが重要です。一般的に、HTTP 429 (Too Many Requests), 500 (Internal Server Error), 503 (Service Unavailable) はサーバー側の一時的な問題であるためリトライ対象とします。一方で、HTTP 401 (Unauthorized), 400 (Bad Request) はリクエスト自体に問題がある恒久的なエラーなので、リトライ対象外とすべきです。

次に、無限ループを防ぐために最大リトライ回数と最大バックオフ時間を設定します。多くのケースでは、最大リトライ回数は3回から5回、最大バックオフ時間は30秒から60秒程度が適切な出発点となります。そして、バックオフ時間には必ずランダムジッターを加えるように実装します。待機時間に計算結果の10%から50%程度の揺らぎを持たせることで、複数クライアントからの同時リトライを効果的に分散させることができます。最後に、リトライの頻度、成功率、エラーの種類を詳細にログとして記録し、そのデータを基に定期的にパラメータをチューニングすることが、システムの安定性を長期的に維持する鍵となります。

## サンプルコード
以下に適応的バックオフによるリトライ戦略のサンプルコードとともに、実装方法を解説します。

なお、本書にはサンプルコード全文を収録しておりません。全文を確認したい場合は、以下のGitHubリポジトリを参照してください。

https://github.com/shibuiwilliam/llm-best-practice-book-program/tree/main/chapter_2/section_4

例では、フィクションのキャラクターをLLMで生成しつつ、リトライ戦略を実装します。

### バックオフ時間の計算とエラー判定

まず、エクスポネンシャルバックオフの計算ロジックと、リトライ対象エラーの判定ロジックを定義します。

```python
# src/service/request_llm.py
MAX_RETRIES = 5
MAX_BACKOFF_SECONDS = 60
BASE_BACKOFF_SECONDS = 1
JITTER_MIN = 0.1  # 10% jitter
JITTER_MAX = 0.5  # 50% jitter

def calculate_backoff_with_jitter(attempt: int, base: float = BASE_BACKOFF_SECONDS) -> float:
    """指数関数的バックオフ時間をランダムジッターと共に計算"""
    backoff = min(base * (2**attempt), MAX_BACKOFF_SECONDS)
    jitter_range = backoff * (JITTER_MAX - JITTER_MIN)
    jitter = random.uniform(backoff * JITTER_MIN, backoff * JITTER_MIN + jitter_range)
    return backoff + jitter

def should_retry_error(error: Exception) -> tuple[bool, int | None]:
    """エラーがリトライ対象か判定"""
    # Google Gemini のリトライ可能エラー
    if isinstance(error, google_exceptions.ResourceExhausted):
        return True, None
    if isinstance(error, (google_exceptions.ServiceUnavailable, ...)):
        return True, None
    # 未知のエラーはリトライしない
    return False, None
```

### リトライデコレータの実装

次に、リトライロジックをデコレータとして実装します。

```python
# src/service/request_llm.py
def retry_with_exponential_backoff(max_retries: int = MAX_RETRIES):
    """エクスポネンシャルバックオフによるリトライロジックを実装するデコレータ"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    should_retry, retry_after = should_retry_error(e)
                    if not should_retry or attempt == max_retries:
                        logger.error(f"Request failed after {attempt + 1} attempts.")
                        raise

                    # バックオフ時間の計算
                    if retry_after is not None:
                        backoff_time = retry_after  # Retry-Afterヘッダーを優先
                    else:
                        backoff_time = calculate_backoff_with_jitter(attempt)

                    logger.warning(f"Retrying in {backoff_time:.2f}s...")
                    await asyncio.sleep(backoff_time)
        return wrapper
    return decorator
```

### LLMリクエストへの適用

リトライデコレータを使用して、LLM APIへのリクエスト関数を定義します。

```python
# src/service/request_llm.py
@retry_with_exponential_backoff()
async def request_gemini(
    character_request: CharacterRequest,
    model: GeminiModel,
    llmops_logger: LLMOpsLogger,
    user_id: str = "default_user",
) -> CharacterResponse:
    """Geminiからキャラクター生成をリクエスト(リトライ機能付き)"""
    prompt = make_prompt(character_request)

    async with llmops_logger.track_llm_request(
        model=model, prompt_content=prompt, user_id=user_id
    ) as tracking:
        result = await google_genai_client.aio.models.generate_content(...)
        tracking["response"] = result.parsed.model_dump()
        return result.parsed
```

### バッチ処理とセマフォによる並行数制御

複数のリクエストを効率的に処理するため、セマフォを使用して並行実行数を制限します。

```python
# src/service/request_llm.py
async def batch_request_gemini(
    character_requests: list[CharacterRequest],
    parallelism: int = 5,
    ...
) -> list[CharacterResponse]:
    """複数のキャラクター生成リクエストをバッチ処理"""
    # セマフォで並行リクエスト数を制限
    semaphore = asyncio.Semaphore(parallelism)

    async def request_with_semaphore(req: CharacterRequest):
        async with semaphore:
            return await request_gemini(req, ...)

    # 制御された並行数で全リクエストを処理
    tasks = [request_with_semaphore(req) for req in character_requests]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # 成功と失敗を分離
    successful_results = [r for r in results if not isinstance(r, Exception)]
    failed_requests = [i for i, r in enumerate(results) if isinstance(r, Exception)]

    logger.info(f"Successful: {len(successful_results)}, Failed: {len(failed_requests)}")
    return successful_results
```

### 出力されるログの例

**リトライ発生時のログ:**
```
[WARNING] Request failed (attempt 1/6). Error: ServiceUnavailable. Retrying in 1.23s...
[WARNING] Request failed (attempt 2/6). Error: ServiceUnavailable. Retrying in 2.87s...
[INFO] Request succeeded after 3 attempts.
```

**レート制限発生時のログ:**
```
[WARNING] Rate limit hit (attempt 1/6). Retry-After: 10s. Waiting...
[INFO] Request succeeded after retry.
```

このサンプルコードでは、エクスポネンシャルバックオフ、ランダムジッター、インテリジェントなエラー判定、セマフォによる並行制御を統合した堅牢なリトライ戦略を実装しています。デコレータパターンを使用することで、既存のコードに簡単にリトライ機能を追加でき、保守性と再利用性が向上します。完全な実装はGitHubリポジトリを参照してください。

## 注意点とトレードオフ
リトライによる処理の遅延は避けられないため、リアルタイム性が厳しく求められるシナリオでは慎重な設計が必要です。例えば、対話型のAIアシスタントにおいて、リトライによって応答が10秒以上遅延すると、ユーザーは応答を待ちきれずにセッションを離脱してしまう可能性が高まります。このような場合は、初回リトライまでの時間を短く設定し、2回から3回程度のリトライで成功しなかった場合は、処理を諦めて「現在、回答を生成できません。少し時間をおいてから再度お試しください」といったフォールバックメッセージを返す設計が適切です。

また、バックオフ戦略の設計が不適切な場合、かえって新たな問題を引き起こす可能性もあります。バックオフ時間が短すぎると、APIサーバーが回復する前にリトライを繰り返してしまい、負荷を十分に分散できず、レート制限がさらに厳しくなるという悪循環に陥ります。逆に、バックオフ時間が長すぎると、一時的な障害がすぐに解消された後も、システムは不必要に長い時間待機することになり、全体のスループットが低下します。APIの仕様やシステムの特性を考慮し、実際の運用データに基づいて継続的に調整することが不可欠です。

## まとめ
LLMリクエストにおける適応的バックオフによるリトライは、外部APIと通信するシステムの信頼性を大幅に向上させる、基本的かつ極めて効果的な戦略です。指数関数的な待機時間の調整とランダムジッターを組み合わせることで、一時的な障害に対してシステムが自動的に復旧し、APIサーバーへの負荷集中を防ぐことができます。適切なエラー判定ロジックと、実データに基づいたパラメータ設定を組み合わせることで、システムの可用性と効率性を両立させることが可能となります。
