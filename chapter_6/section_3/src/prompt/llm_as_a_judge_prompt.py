import json

from src.model.llm_as_a_judge_model import JudgeRequest, JudgeResponse


def make_openai_judge_prompt(request: JudgeRequest) -> list:
    params = JudgeResponse.detailed_model()
    param_dump = json.dumps(params, indent=2, ensure_ascii=False)

    evaluation_content = f"""以下の質問と回答を評価してください。

【質問】
{request.question}

【回答】
{request.response}
"""

    if request.request_parameters:
        evaluation_content += f"""
【リクエストパラメータ】
{request.request_parameters}
"""

    if request.context:
        evaluation_content += f"""
【参照情報】
{request.context}
"""

    return [
        {
            "role": "system",
            "content": f"""あなたは優秀なレビュアーです。
提示された質問と回答を読み、以下の評価軸について1から5の5段階で評価し、その理由と評価結果を簡潔に述べてください。

【評価軸】
1. 正確性 (accuracy): 回答が質問に対して正確かつ事実として正しいか
   - リクエストパラメータがある場合、その要件に忠実であるか
   - 参照情報がある場合、その内容に忠実であるか
   - 誤った情報やハルシネーションが含まれていないか

2. 網羅性 (comprehensiveness): 質問に対して必要な情報が十分に含まれているか
   - リクエストパラメータで指定された要件をすべて満たしているか
   - ユーザーの質問に直接答えているか
   - 重要な情報が欠けていないか

3. 明瞭さ (clarity): 回答が理解しやすく、適切な表現で書かれているか
   - 不必要な専門用語を使っていないか
   - 文章構造が読みやすいか

【評価基準】
- 1点: 完全に不適切 (誤情報が多い、質問に答えていない、理解不能)
- 2点: 不十分 (部分的に誤り、重要な情報が欠けている、わかりにくい)
- 3点: 許容範囲 (概ね正しいが改善の余地あり)
- 4点: 良好 (正確で適切、わずかな改善点あり)
- 5点: 完璧 (非常に正確、完全、明瞭)

評価結果は以下のJSON構造で出力してください：

{param_dump}

注意事項：
- 必ず上記3つの評価軸すべてについて評価を行うこと
- overall_scoreは各評価軸のスコアの平均値とすること
- summaryには総合的な評価を1-2文で簡潔にまとめること
- JSON構造の外に説明や追加のテキストを含めないこと
- 応答は有効なJSONであること
""",
        },
        {
            "role": "user",
            "content": evaluation_content,
        },
    ]


# def make_gemini_judge_prompt(request: JudgeRequest) -> tuple[str, str]:
#     params = JudgeResponse.detailed_model()
#     param_dump = json.dumps(params, indent=2, ensure_ascii=False)
#
#     system_prompt = f"""あなたは優秀なレビュアーです。
# 提示された質問と回答を読み、以下の評価軸について1から5の5段階で評価し、その理由と評価結果を簡潔に述べてください。
#
# 【評価軸】
# 1. 正確性 (accuracy): 回答が質問に対して正確かつ事実として正しいか
#    - リクエストパラメータがある場合、その要件に忠実であるか
#    - 参照情報がある場合、その内容に忠実であるか
#    - 誤った情報やハルシネーションが含まれていないか
#
# 2. 網羅性 (comprehensiveness): 質問に対して必要な情報が十分に含まれているか
#    - リクエストパラメータで指定された要件をすべて満たしているか
#    - ユーザーの質問に直接答えているか
#    - 重要な情報が欠けていないか
#
# 3. 明瞭さ (clarity): 回答が理解しやすく、適切な表現で書かれているか
#    - 不必要な専門用語を使っていないか
#    - 文章構造が読みやすいか
#
# 【評価基準】
# - 1点: 完全に不適切 (誤情報が多い、質問に答えていない、理解不能)
# - 2点: 不十分 (部分的に誤り、重要な情報が欠けている、わかりにくい)
# - 3点: 許容範囲 (概ね正しいが改善の余地あり)
# - 4点: 良好 (正確で適切、わずかな改善点あり)
# - 5点: 完璧 (非常に正確、完全、明瞭)
#
# 評価結果は以下のJSON構造で出力してください：
#
# {param_dump}
#
# 注意事項：
# - 必ず上記3つの評価軸すべてについて評価を行うこと
# - overall_scoreは各評価軸のスコアの平均値とすること
# - summaryには総合的な評価を1-2文で簡潔にまとめること
# - JSON構造の外に説明や追加のテキストを含めないこと
# - 応答は有効なJSONであること
# """
#
#     evaluation_content = f"""以下の質問と回答を評価してください。
#
# 【質問】
# {request.question}
#
# 【回答】
# {request.response}
# """
#
#     if request.request_parameters:
#         evaluation_content += f"""
# 【リクエストパラメータ】
# {request.request_parameters}
# """
#
#     if request.context:
#         evaluation_content += f"""
# 【参照情報】
# {request.context}
# """
#
#     return system_prompt, evaluation_content


def make_anthropic_judge_prompt(request: JudgeRequest) -> list:
    params = JudgeResponse.detailed_model()
    param_dump = json.dumps(params, indent=2, ensure_ascii=False)

    evaluation_content = f"""以下の質問と回答を評価してください。

【質問】
{request.question}

【回答】
{request.response}
"""

    if request.request_parameters:
        evaluation_content += f"""
【リクエストパラメータ】
{request.request_parameters}
"""

    if request.context:
        evaluation_content += f"""
【参照情報】
{request.context}
"""

    return [
        {
            "role": "user",
            "content": f"""あなたは優秀なレビュアーです。
提示された質問と回答を読み、以下の評価軸について1から5の5段階で評価し、その理由と評価結果を簡潔に述べてください。

【評価軸】
1. 正確性 (accuracy): 回答が質問に対して正確かつ事実として正しいか
   - リクエストパラメータがある場合、その要件に忠実であるか
   - 参照情報がある場合、その内容に忠実であるか
   - 誤った情報やハルシネーションが含まれていないか

2. 網羅性 (comprehensiveness): 質問に対して必要な情報が十分に含まれているか
   - リクエストパラメータで指定された要件をすべて満たしているか
   - ユーザーの質問に直接答えているか
   - 重要な情報が欠けていないか

3. 明瞭さ (clarity): 回答が理解しやすく、適切な表現で書かれているか
   - 不必要な専門用語を使っていないか
   - 文章構造が読みやすいか

【評価基準】
- 1点: 完全に不適切 (誤情報が多い、質問に答えていない、理解不能)
- 2点: 不十分 (部分的に誤り、重要な情報が欠けている、わかりにくい)
- 3点: 許容範囲 (概ね正しいが改善の余地あり)
- 4点: 良好 (正確で適切、わずかな改善点あり)
- 5点: 完璧 (非常に正確、完全、明瞭)

評価結果は以下のJSON構造で出力してください：

{param_dump}

注意事項：
- 必ず上記3つの評価軸すべてについて評価を行うこと
- overall_scoreは各評価軸のスコアの平均値とすること
- summaryには総合的な評価を1-2文で簡潔にまとめること
- JSON構造の外に説明や追加のテキストを含めないこと
- 応答は有効なJSONであること

{evaluation_content}
""",
        },
    ]


def make_custom_openai_judge_prompt(
    request: JudgeRequest,
    criteria: list[dict[str, str]],
    scoring_guide: str | None = None,
) -> list:
    params = JudgeResponse.detailed_model()
    param_dump = json.dumps(params, indent=2, ensure_ascii=False)

    criteria_text = "\n".join([f"{i + 1}. {c['name']}: {c['description']}" for i, c in enumerate(criteria)])

    if not scoring_guide:
        scoring_guide = """- 1点: 完全に不適切
- 2点: 不十分
- 3点: 許容範囲
- 4点: 良好
- 5点: 完璧"""

    evaluation_content = f"""以下の質問と回答を評価してください。

【質問】
{request.question}

【回答】
{request.response}
"""

    if request.context:
        evaluation_content += f"""
【参照情報】
{request.context}
"""

    return [
        {
            "role": "system",
            "content": f"""あなたは優秀なレビュアーです。
提示された質問と回答を読み、以下の評価軸について1から5の5段階で評価し、その理由を簡潔に述べてください。

【評価軸】
{criteria_text}

【評価基準】
{scoring_guide}

評価結果は以下のJSON構造で出力してください：

{param_dump}

注意事項：
- 必ずすべての評価軸について評価を行うこと
- overall_scoreは各評価軸のスコアの平均値とすること
- summaryには総合的な評価を1-2文で簡潔にまとめること
- JSON構造の外に説明や追加のテキストを含めないこと
- 応答は有効なJSONであること
""",
        },
        {
            "role": "user",
            "content": evaluation_content,
        },
    ]


# def make_custom_gemini_judge_prompt(
#     request: JudgeRequest,
#     criteria: list[dict[str, str]],
#     scoring_guide: str | None = None,
# ) -> tuple[str, str]:
#     params = JudgeResponse.detailed_model()
#     param_dump = json.dumps(params, indent=2, ensure_ascii=False)
#
#     criteria_text = "\n".join([f"{i + 1}. {c['name']}: {c['description']}" for i, c in enumerate(criteria)])
#
#     if not scoring_guide:
#         scoring_guide = """- 1点: 完全に不適切
# - 2点: 不十分
# - 3点: 許容範囲
# - 4点: 良好
# - 5点: 完璧"""
#
#     system_prompt = f"""あなたは優秀なレビュアーです。
# 提示された質問と回答を読み、以下の評価軸について1から5の5段階で評価し、その理由を簡潔に述べてください。
#
# 【評価軸】
# {criteria_text}
#
# 【評価基準】
# {scoring_guide}
#
# 評価結果は以下のJSON構造で出力してください：
#
# {param_dump}
#
# 注意事項：
# - 必ずすべての評価軸について評価を行うこと
# - overall_scoreは各評価軸のスコアの平均値とすること
# - summaryには総合的な評価を1-2文で簡潔にまとめること
# - JSON構造の外に説明や追加のテキストを含めないこと
# - 応答は有効なJSONであること
# """
#
#     evaluation_content = f"""以下の質問と回答を評価してください。
#
# 【質問】
# {request.question}
#
# 【回答】
# {request.response}
# """
#
#     if request.context:
#         evaluation_content += f"""
# 【参照情報】
# {request.context}
# """
#
#     return system_prompt, evaluation_content


def make_custom_anthropic_judge_prompt(
    request: JudgeRequest,
    criteria: list[dict[str, str]],
    scoring_guide: str | None = None,
) -> list:
    params = JudgeResponse.detailed_model()
    param_dump = json.dumps(params, indent=2, ensure_ascii=False)

    criteria_text = "\n".join([f"{i + 1}. {c['name']}: {c['description']}" for i, c in enumerate(criteria)])

    if not scoring_guide:
        scoring_guide = """- 1点: 完全に不適切
- 2点: 不十分
- 3点: 許容範囲
- 4点: 良好
- 5点: 完璧"""

    evaluation_content = f"""以下の質問と回答を評価してください。

【質問】
{request.question}

【回答】
{request.response}
"""

    if request.context:
        evaluation_content += f"""
【参照情報】
{request.context}
"""

    return [
        {
            "role": "user",
            "content": f"""あなたは優秀なレビュアーです。
提示された質問と回答を読み、以下の評価軸について1から5の5段階で評価し、その理由を簡潔に述べてください。

【評価軸】
{criteria_text}

【評価基準】
{scoring_guide}

評価結果は以下のJSON構造で出力してください：

{param_dump}

注意事項：
- 必ずすべての評価軸について評価を行うこと
- overall_scoreは各評価軸のスコアの平均値とすること
- summaryには総合的な評価を1-2文で簡潔にまとめること
- JSON構造の外に説明や追加のテキストを含めないこと
- 応答は有効なJSONであること

{evaluation_content}
""",
        },
    ]
