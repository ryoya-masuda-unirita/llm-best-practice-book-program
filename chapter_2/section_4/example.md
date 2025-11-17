# 第2項　LLMOpsのための構造化ログ

## 概要

ソフトウェアにおいてログを出力し記録する有効性は広く認識されているでしょう。更にいうと、ログを一貫性のある構造化フォーマットで出力することは、ログの解析性と活用性を大幅に向上させます。LLMOpsにおいても同様であり、LLMを利用したアプリケーションの運用監視、品質分析、トラブルシューティングを効果的に行うためには、構造化ログの導入が不可欠です。

LLMOpsのための構造化ログでは、LLMを活用するアプリケーションにおいて、プロンプト、レスポンス、利用したモデルやAPI、その他関連するメタ情報やパラメータを構造化された形式でログ出力する設計手法です。このプラクティスを導入することで、LLMの運用監視、品質分析、テスト自動化、そしてトラブルシューティングを効率的に実行できるようになります。構造化されたログは、DatadogやNew Relic、BigQueryといったログ集約基盤と連携し、データの可視化や異常検知を実現する基盤となります。本項では、ログの可読性と安全性を両立させるため、プロンプト本文を専用のデータストアに分離して管理する方法も解説します。LLMシステムの信頼性とトレーサビリティを確保することを目指します。


## 解決したい課題

LLMの推論プロセスには、入力プロンプト、モデルの出力、使用モデル、設定パラメータ、リクエスト時刻、実行ユーザーといった多様な要素が関わっています。一般的なソフトウェア開発と同様に、障害発生時にどの情報が原因であったかを特定するには、その時点での記録が不可欠です。記録されていない情報は後から追うことができません。問題解決や品質改善のボトルネックを分析するためには、必要十分な情報をログとして出力しておく必要があります。

具体的な例として、商用チャットボトットサービスで、ユーザーから「回答が的外れだった」という報告を受けたケースを考えてみます。このとき、どのようなプロンプトが使われ、どういうパラメータ設定で送信されたのかが不明瞭であれば、問題の再現や調査は極めて困難になります。また、同じモデルでも`temperature`パラメータや`reasoning`パラメータの違いで出力は大きく変わりますが、これらの情報が記録されていなければ、どの設定が最適だったのかを後から分析することはできません。

## 解決策の提案

これらの課題を解決するため、LLMへのリクエストとレスポンスに関する情報を、一貫した構造化ログとして記録します。これにより、ログの機械的な解析や品質モニタリングが格段に容易になります。先に挙げたチャットボットの例では、構造化ログによって特定のユーザーからの問い合わせに対して、使用されたプロンプトや`temperature`の設定値を即座に特定できます。これにより、同じ条件で問題を再現し、パラメータを調整して回答精度を改善するといった具体的なアクションに繋がります。

加えて重要なのは、長文のプロンプト本文をログストリームに直接出力せず、専用のデータストア（Amazon S3など）に別途保存するアプローチです。ログストリームにはデータストアへの参照IDのみを記録し、必要に応じて双方の情報を突き合わせることで、ログの可読性とセキュリティを両立させます。

| フィールド名 | 説明 |
| :--: | :--: |
| `timestamp` | ログの記録時刻 |
| `request_id` | リクエスト全体を識別する一意なID |
| `prompt_id` | プロンプト本文をデータストアから特定するための一意なID |
| `user_id` | ユーザー識別子 |
| `model` | 使用したLLMモデル名 |
| `temperature` | 生成時の温度パラメータ |
| `latency_ms` | 応答時間（ミリ秒） |
| `status_code` | API呼び出しのステータスコード |

このデータストアへの保存処理は、システムの応答性能に影響を与えないよう、KafkaやRabbitMQ、Redisのようなメッセージキューを利用して非同期で実行することが推奨されます。


## 適用するユースケース

このプラクティスは、特にLLMを用いた商用アプリケーションにおける運用監視とSLA（サービス品質保証）準拠の場面で極めて有効です。大規模なカスタマーサポートシステムでLLMを活用している企業では、日々数万件の問い合わせが処理されるでしょう。構造化ログにより、各問い合わせの応答時間やエラー率、ユーザー満足度を定量的に監視し、SLAで定められた品質が維持されているかを確認します。特定のプロンプトパターンで応答が遅延する傾向を発見し、プロンプトの最適化によって改善することも可能です。

もう一つの重要なユースケースは、RAGやAIエージェントのように高頻度でプロンプトを生成するアプリケーションです。企業の社内文書検索システムで1日に数十万回のクエリが実行される場合、構造化ログは宝の山となります。どの文書が頻繁に参照され、どのような質問が多いかを分析し、その結果を基にキャッシュ戦略を最適化したり、頻出する質問への専用処理フローを構築したりすることで、システム全体の性能と精度を向上させることができます。


## 導入のポイント

このプラクティスを効果的に導入するための最初のステップは、ログスキーマの明確な定義です。組織内の全てのLLM呼び出しで統一された形式を用いるため、共通ライブラリを整備することが重要です。例えばPythonでは、専用のロギングクラスを作成し、タイムスタンプやIDの自動生成、メタデータ収集の機能を実装します。開発段階からログレベル（INFO, DEBUG, ERROR）を適切に使い分け、本番環境では必要最小限の情報のみが出力されるよう制御してください。

また、プロンプトや出力に含まれる個人情報については、正規表現や固有表現抽出（NER）モデルを用いて自動的にマスキングするロジックを組み込むことが不可欠です。プロンプトの保存処理は、メインの推論処理をブロックしないよう、メッセージキューを介したバックグラウンドでの非同期実行を徹底します。保存先のストレージは、`s3://prompt-logs/2024/03/15/request-123.json`のように時系列ベースで整理し、日付でパーティション分割することで検索効率を高めます。環境ごとに適切なログ保存期間（TTL）を設定し、古いログは自動的にアーカイブまたは削除する仕組みを構築することも、コスト管理の観点から重要です。

加えて、既存のLLMOpsツールを導入することも重要な検討事項です。LangfuseやLangSmithといった主要なLLMOpsツールやオブザーバビリティツールでは、プロンプトやLLMセッション（ユーザとLLMの一連のやり取り）のトレース機能は標準で提供されています。これらのツールを活用することで、ログ収集、保存、分析のプロセスを大幅に簡素化できます。他方で、それぞれに独自要件があり、かつライブラリと基盤を独自に用意する必要があるため、開発・運用コストに与える影響を十分に評価してください。特に既存のログ基盤と異なるオブザーバビリティを導入する場合、データの一貫性や運用方法、さらにはUIが別れることによる開発・運用者の負担は無視できません。

## サンプルコード
以下に構造化ログを活用したサンプルコードとともに、実装方法を解説します。

なお、本書にはサンプルコード全文を収録しておりません。全文を確認したい場合は、以下のGitHubリポジトリを参照してください。

https://github.com/shibuiwilliam/llm-best-practice-book-program/tree/main/chapter_2/section_2

例では今回はフィクションのキャラクターをLLMで生成しつつ、そのリクエスト、レスポンス、パラメータを構造的にログ出力します。

### 構造化ログエントリのモデル定義

まず、ログエントリの構造を定義します。`LLMOpsLogEntry`は、LLMリクエストのメタデータを保持するPydanticモデルです。プロンプトの内容は含まず、別のデータストアへの参照ID(`prompt_id`)のみを保持します。

```python
# src/model/llmops_log.py
class LLMOpsLogEntry(BaseModel):
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    request_id: str = Field(..., description="リクエスト全体の一意な識別子")
    prompt_id: str = Field(..., description="データストアからプロンプトを取得するための一意な識別子")
    user_id: Optional[str] = Field(None, description="ユーザー識別子")
    model: str = Field(..., description="使用したLLMモデル名")
    temperature: Optional[float] = Field(None, description="生成時の温度パラメータ", ge=0.0, le=2.0)
    latency_ms: Optional[float] = Field(None, description="応答時間(ミリ秒)", ge=0.0)
    status_code: Optional[int] = Field(None, description="APIレスポンスのステータスコード")
    level: LogLevel = Field(default=LogLevel.INFO, description="ログレベル")
    metadata: Optional[dict[str, Any]] = Field(default_factory=dict, description="追加のメタデータ")

    def to_json_string(self) -> str:
        return json.dumps(self.model_dump(exclude_none=True), ensure_ascii=False)
```

### プロンプトデータのモデル定義と個人情報マスキング

次に、プロンプト本文とレスポンスを保存するための`PromptData`モデルを定義します。このモデルには、正規表現ベースの個人情報マスキング機能が含まれています。

```python
# src/model/prompt_data.py
class PromptData(BaseModel):
    prompt_id: str = Field(..., description="プロンプトの一意な識別子")
    prompt_content: Any = Field(..., description="実際のプロンプト内容")
    response_content: Optional[Any] = Field(None, description="LLMレスポンスの内容")
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: Optional[dict[str, Any]] = Field(default_factory=dict)

    def mask_sensitive_data(self) -> None:
        patterns = [
            (r"\b\d{3}-\d{2}-\d{4}\b", "***-**-****"),  # SSN
            (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "***@***.***"),  # Email
            (r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b", "****-****-****-****"),  # クレジットカード
        ]
        # マスキング処理の実装(詳細はGitHubを参照)
        ...
```

### LLMOpsロガーの実装

`LLMOpsLogger`は、構造化ログとプロンプトストレージを統合する中心的なコンポーネントです。コンテキストマネージャーを使用して、自動的にタイミング計測とエラーハンドリングを行います。

```python
# src/service/llmops_logger.py
class LLMOpsLogger:
    @asynccontextmanager
    async def track_llm_request(
        self,
        model: str,
        prompt_content: Any,
        temperature: Optional[float] = None,
        user_id: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> AsyncGenerator[dict[str, str], None]:
        """LLMリクエストのタイミングとログを自動的に追跡"""
        request_id = str(uuid4())
        prompt_id = str(uuid4())
        tracking = {"request_id": request_id, "prompt_id": prompt_id, "response": None}

        start_time = time.time()
        try:
            yield tracking
            status_code = 200
        except Exception as e:
            status_code = 500
            level = LogLevel.ERROR
            raise
        finally:
            latency_ms = (time.time() - start_time) * 1000
            await self.log_llm_request(
                request_id, prompt_id, model, prompt_content,
                tracking.get("response"), user_id, latency_ms, status_code, metadata
            )

    async def log_llm_request(self, request_id, prompt_id, model, prompt_content, ...):
        # 構造化ログエントリを作成
        log_entry = LLMOpsLogEntry(request_id=request_id, prompt_id=prompt_id, ...)
        # プロンプトデータを別途保存
        prompt_data = PromptData(prompt_id=prompt_id, prompt_content=prompt_content, ...)
        await self._store_prompt_async(prompt_data)
        # ログ出力
        self.logger.info(log_entry.to_json_string())
```

### 実際のLLMリクエストでの使用例

コンテキストマネージャーを使用することで、タイミング計測とエラーハンドリングが自動的に行われます。

```python
# src/service/request_llm.py
async def request_anthropic(
    model: str,
    llmops_logger: LLMOpsLogger,
    user_id: str = "default_user",
) -> CharacterResponse:
    """Anthropic Claudeから構造化ログ付きでキャラクター生成をリクエスト"""
    prompt = make_anthropic_prompt()

    async with llmops_logger.track_llm_request(
        model=model,
        prompt_content=prompt,
        user_id=user_id,
        metadata={"provider": "anthropic"},
    ) as tracking:
        result = await anthropic_client.beta.messages.parse(
            model=model,
            max_tokens=1024,
            messages=prompt,
            output_format=CharacterResponse,
        )
        tracking["response"] = result.parsed_output.model_dump() if result.parsed_output else None
        return result.parsed_output
```

### 出力されるログの例

**標準出力への構造化ログ(メタデータのみ):**
```json
{
  "timestamp": "2024-03-15T10:30:45.123456+00:00",
  "request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "prompt_id": "p1q2r3s4-t5u6-v7w8-xyz9-ab1234567890",
  "user_id": "user123",
  "model": "gpt-4o-mini",
  "latency_ms": 1234.56,
  "status_code": 200,
  "level": "INFO"
}
```

**データストアに保存されるプロンプト(`prompt_storage/2024/03/15/p1q2r3s4...json`):**
```json
{
  "prompt_id": "p1q2r3s4-t5u6-v7w8-xyz9-ab1234567890",
  "prompt_content": [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}],
  "response_content": {"first_name": "Akira", "last_name": "Tanaka", "age": 28},
  "created_at": "2024-03-15T10:30:45.123456"
}
```

このサンプルコードでは統一されたロギングインターフェースを提供しています。コンテキストマネージャーパターンを使用することで、手動でタイミング計測やエラーハンドリングを実装する必要がなくなり、コードの保守性と一貫性が向上します。完全な実装はGitHubリポジトリを参照してください。


## 注意点とトレードオフ

このプラクティスを採用する上で最も注意すべきは、個人情報や機密情報の取り扱いです。例えば、医療分野でLLMを活用するシステムでは、患者の病歴といった機密情報がプロンプトに含まれる可能性があります。これらの情報が不適切にログ記録されることは個人情報保護のもとで重大なコンプライアンス問題を引き起こしかねません。保護対象の医療情報を自動で検出しマスキングする仕組みが必要ですが、このような高度なフィルタリング処理はシステムの複雑性を増大させ、開発・保守コストが上昇するというトレードオフが発生します。

次に、ストレージコストの増大も重要な検討事項です。チャットボットサービスで、仮に1日に100万件のリクエストを処理するとします。1リクエストあたり平均5KBのログデータが生成される場合、1日で5GB、年間で約1.8TBものデータになります。このコストを管理するためには、重要度の高いログのみを記録したり、古いログを低コストのアーカイブストレージに移動したりする対策が必要ですが、これにより過去データへのアクセス速度が低下するというトレードオフが生じます。また、ログ処理自体がシステムの応答時間に影響を与える可能性も考慮し、非同期処理を導入する必要がありますが、これもまたシステムの複雑性を増し、稀にログが欠損するリスクを伴います。


## まとめ

LLMOpsのための構造化ログは、LLMを業務活用する上での信頼性、トレーサビリティ、品質管理を強化するための、基本的かつ極めて重要な設計プラクティスです。構造化されたログを標準化し、分析・可視化基盤と連携させることで、開発から運用、改善に至る全てのフェーズで大きな効果を発揮します。ただし、プライバシー保護、ストレージコスト、パフォーマンスへの影響といったトレードオフを十分に理解し、適切なバランスを取りながら実装することが成功の鍵となります。
