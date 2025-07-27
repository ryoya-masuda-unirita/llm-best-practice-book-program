import json
from typing import Any, Dict, List

from pydantic import BaseModel, Field

from src.llms import google_genai_client, openai_client
from src.logger import make_logger
from src.model import CharacterResponse, LLMProvider

logger = make_logger(__name__)


class EvaluationResult(BaseModel):
    """構造化された評価結果モデル"""

    reason: str = Field(..., description="評価理由")
    accuracy_score: int = Field(..., description="正確性スコア（1-5）", ge=1, le=5)
    completeness_score: int = Field(..., description="網羅性スコア（1-5）", ge=1, le=5)
    clarity_score: int = Field(..., description="明瞭さスコア（1-5）", ge=1, le=5)
    feedback: str = Field(..., description="改善のためのフィードバック")

    @property
    def average_score(self) -> float:
        """平均スコアを計算"""
        return (self.accuracy_score + self.completeness_score + self.clarity_score) / 3

    def save_as_json(self, file_path: str) -> None:
        """評価結果をJSONファイルとして保存"""
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(self.model_dump(), f, indent=4, ensure_ascii=False)


def make_evaluation_prompt(
    original_prompt: str, generated_response: str, evaluation_criteria: str = None
) -> List[Dict[str, str]]:
    """評価用のプロンプトを生成する

    Args:
        original_prompt: 元のプロンプト
        generated_response: 評価対象の生成結果
        evaluation_criteria: 追加の評価基準（オプション）

    Returns:
        評価用プロンプトのメッセージリスト
    """

    # デフォルトの評価基準
    default_criteria = """
評価基準：

正確性スコア（1-5点）:
1: 情報が完全に間違っている、または事実と反する内容が含まれている
2: 重要な情報が欠けている、または部分的に間違った情報が含まれている  
3: 基本的な情報は正しいが、詳細や文脈に誤りがある
4: 情報は正確だが、一部の細かい点で改善の余地がある
5: すべての情報が正確で、事実に基づいた適切な内容である

網羅性スコア（1-5点）:
1: 要求された情報の大部分が欠けている
2: 要求された情報の一部が欠けている
3: 基本的な情報は含まれているが、詳細が不足している
4: ほぼすべての要求された情報が含まれている
5: 要求されたすべての情報が完全に含まれている

明瞭さスコア（1-5点）:
1: 読みにくく、理解が困難
2: 一部わかりにくい箇所がある
3: 基本的には理解できるが、改善の余地がある
4: 明確で理解しやすい
5: 非常に明確で、完璧に理解しやすい
"""

    criteria = evaluation_criteria if evaluation_criteria else default_criteria

    # EvaluationResultのスキーマを取得
    schema = EvaluationResult.model_json_schema()
    schema_str = json.dumps(schema, ensure_ascii=False, indent=2)

    system_content = f"""あなたは厳格で公正なLLM出力評価者です。
与えられたプロンプトとそれに対する生成結果を以下の基準で評価してください。

{criteria}

評価は以下のJSON構造で出力してください：
{schema_str}

評価では以下を重視してください：
1. 客観的で一貫した評価基準を適用する
2. 具体的で建設的なフィードバックを提供する
3. 評価理由を明確に説明する
4. JSON構造の外に説明や追加のテキストを含めない
"""

    user_content = f"""以下のプロンプトと生成結果を評価してください：

【元のプロンプト】
{original_prompt}

【生成結果】
{generated_response}

上記の内容を評価基準に従って評価し、構造化されたJSON形式で結果を出力してください。"""

    return [{"role": "system", "content": system_content}, {"role": "user", "content": user_content}]


async def evaluate_with_openai(
    original_prompt: str, generated_response: str, evaluation_criteria: str = None
) -> EvaluationResult:
    """OpenAIを使用してLLM出力を評価する

    Args:
        original_prompt: 元のプロンプト
        generated_response: 評価対象の生成結果
        evaluation_criteria: 追加の評価基準（オプション）

    Returns:
        構造化された評価結果
    """
    prompt = make_evaluation_prompt(original_prompt, generated_response, evaluation_criteria)

    result = await openai_client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=prompt,
        response_format=EvaluationResult,
        temperature=0.1,  # 評価の一貫性のため低い温度設定
    )

    return result.choices[0].message.parsed


async def evaluate_with_gemini(
    original_prompt: str, generated_response: str, evaluation_criteria: str = None
) -> EvaluationResult:
    """Geminiを使用してLLM出力を評価する

    Args:
        original_prompt: 元のプロンプト
        generated_response: 評価対象の生成結果
        evaluation_criteria: 追加の評価基準（オプション）

    Returns:
        構造化された評価結果
    """
    from google.genai.types import GenerateContentConfig

    prompt = make_evaluation_prompt(original_prompt, generated_response, evaluation_criteria)

    result = await google_genai_client.aio.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt[-1]["content"],
        config=GenerateContentConfig(
            system_instruction=prompt[0]["content"],
            response_mime_type="application/json",
            response_schema=EvaluationResult,
            temperature=0.1,  # 評価の一貫性のため低い温度設定
        ),
    )

    logger.info(f"Gemini evaluation result: {result}")
    return result.parsed


async def evaluate_character_response(
    character_response: CharacterResponse,
    original_prompt: str,
    judge_provider: LLMProvider = LLMProvider.GEMINI,
    evaluation_criteria: str = None,
) -> EvaluationResult:
    """キャラクター生成結果を評価する

    Args:
        character_response: 評価対象のキャラクター応答
        original_prompt: 元のプロンプト文字列
        judge_provider: 評価に使用するLLMプロバイダー
        evaluation_criteria: 追加の評価基準（オプション）

    Returns:
        構造化された評価結果
    """
    # CharacterResponseをJSON文字列に変換
    generated_response = json.dumps(character_response.model_dump(), ensure_ascii=False, indent=2)

    if judge_provider == LLMProvider.OPENAI:
        return await evaluate_with_openai(original_prompt, generated_response, evaluation_criteria)
    elif judge_provider == LLMProvider.GEMINI:
        return await evaluate_with_gemini(original_prompt, generated_response, evaluation_criteria)
    else:
        raise ValueError(f"Unsupported judge provider: {judge_provider.value}")


async def batch_evaluate_responses(
    responses: List[Dict[str, Any]], judge_provider: LLMProvider = LLMProvider.GEMINI, evaluation_criteria: str = None
) -> List[EvaluationResult]:
    """複数の応答を一括評価する

    Args:
        responses: 評価対象の応答リスト。各要素は{"prompt": str, "response": str}の辞書
        judge_provider: 評価に使用するLLMプロバイダー
        evaluation_criteria: 追加の評価基準（オプション）

    Returns:
        評価結果のリスト
    """
    results = []

    for i, response_data in enumerate(responses):
        logger.info(f"Evaluating response {i + 1}/{len(responses)}")

        if judge_provider == LLMProvider.OPENAI:
            result = await evaluate_with_openai(response_data["prompt"], response_data["response"], evaluation_criteria)
        elif judge_provider == LLMProvider.GEMINI:
            result = await evaluate_with_gemini(response_data["prompt"], response_data["response"], evaluation_criteria)
        else:
            raise ValueError(f"Unsupported judge provider: {judge_provider.value}")

        results.append(result)

        # APIレート制限を考慮した間隔調整
        if i < len(responses) - 1:  # 最後の要素でない場合
            import asyncio

            await asyncio.sleep(0.5)  # 500ms待機

    return results


def filter_low_quality_responses(evaluations: List[EvaluationResult], threshold: float = 3.0) -> List[int]:
    """品質の低い応答のインデックスを特定する

    Args:
        evaluations: 評価結果のリスト
        threshold: 品質の閾値（平均スコア）

    Returns:
        品質が閾値を下回る応答のインデックスリスト
    """
    low_quality_indices = []

    for i, evaluation in enumerate(evaluations):
        if evaluation.average_score < threshold:
            low_quality_indices.append(i)

    return low_quality_indices


def analyze_evaluation_results(evaluations: List[EvaluationResult]) -> Dict[str, Any]:
    """評価結果を分析して統計情報を生成する

    Args:
        evaluations: 評価結果のリスト

    Returns:
        分析結果の辞書
    """
    if not evaluations:
        return {"error": "No evaluations provided"}

    # 各スコアの統計
    accuracy_scores = [e.accuracy_score for e in evaluations]
    completeness_scores = [e.completeness_score for e in evaluations]
    clarity_scores = [e.clarity_score for e in evaluations]
    average_scores = [e.average_score for e in evaluations]

    return {
        "total_evaluations": len(evaluations),
        "accuracy": {
            "mean": sum(accuracy_scores) / len(accuracy_scores),
            "min": min(accuracy_scores),
            "max": max(accuracy_scores),
        },
        "completeness": {
            "mean": sum(completeness_scores) / len(completeness_scores),
            "min": min(completeness_scores),
            "max": max(completeness_scores),
        },
        "clarity": {
            "mean": sum(clarity_scores) / len(clarity_scores),
            "min": min(clarity_scores),
            "max": max(clarity_scores),
        },
        "overall": {
            "mean": sum(average_scores) / len(average_scores),
            "min": min(average_scores),
            "max": max(average_scores),
        },
        "low_quality_count": len([e for e in evaluations if e.average_score < 3.0]),
        "high_quality_count": len([e for e in evaluations if e.average_score >= 4.0]),
    }
