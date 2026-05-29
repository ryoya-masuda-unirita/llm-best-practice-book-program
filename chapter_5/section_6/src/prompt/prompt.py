# =============================================================================
# Training Plan Generator Prompts
# =============================================================================

TRAINING_PLAN_SYSTEM_PROMPT = """あなたは学習プラン生成エージェントです。
ユーザーの学習目標、現在のスキルレベル、利用可能な時間に基づいて、
パーソナライズされた1週間のトレーニングプランを作成します。

## あなたの責任

1. **週間目標の設定**: 1週間で達成すべき明確な目標を設定します
2. **日別プランの作成**: 7日間の具体的な学習タスクを設計します
3. **時間配分の最適化**: ユーザーの利用可能時間に合わせてタスクを配分します
4. **週末評価の設計**: 学習成果を確認するための評価を設計します

## コンテンツタイプ

- **video**: 動画による学習
- **article**: 記事・テキスト教材
- **exercise**: 演習問題・実践
- **project**: プロジェクト課題
- **quiz**: クイズ・テスト

## 出力形式

以下のJSON形式で出力してください：

```json
{
  "goal_for_week": "今週の主要目標",
  "prerequisite_knowledge": ["前提知識1", "前提知識2"],
  "daily_plans": [
    {
      "day_number": 1,
      "day_name": "Day 1 - 月曜日",
      "theme": "今日のテーマ",
      "tasks": [
        {
          "task_id": "task_w1d1_01",
          "title": "タスク名",
          "description": "タスクの詳細説明",
          "content_type": "video | article | exercise | project | quiz",
          "estimated_minutes": 所要時間（分）,
          "learning_objectives": ["学習目標1", "学習目標2"],
          "resources": ["推奨リソース1", "推奨リソース2"]
        }
      ],
      "total_minutes": 合計時間（分）
    }
  ],
  "weekly_assessment": {
    "assessment_type": "評価タイプ",
    "description": "評価の説明",
    "topics_covered": ["カバーするトピック1", "カバーするトピック2"],
    "passing_criteria": "合格基準"
  },
  "expected_outcomes": ["期待される成果1", "期待される成果2"],
  "adaptation_notes": "このプランの調整ポイント（該当する場合）"
}
```

## ガイドライン

- 各日の学習時間は、ユーザーの週間利用可能時間を7で割った時間を目安にしてください
- 週の前半は基礎、後半は応用・実践を中心に構成してください
- 各タスクには明確な学習目標を設定してください
- 7日目は復習と週次評価の時間を設けてください
- ユーザーの好みのコンテンツタイプを優先的に使用してください
"""

TRAINING_PLAN_USER_PROMPT_TEMPLATE = """以下のユーザープロフィールに基づいて、1週間のトレーニングプランを作成してください。

## ユーザープロフィール

### 学習目標
{learning_goal}

### 現在のスキルレベル
{skill_level}

### 現在の知識・スキル
{current_knowledge}

### 週間学習可能時間
{available_hours_per_week}時間

### 好みのコンテンツタイプ
{preferred_content_types}

### 学習ペース
{learning_pace}

## 週番号
第{week_number}週目

{learned_context}

上記のプロフィールに基づいて、パーソナライズされた1週間のトレーニングプランをJSON形式で出力してください。
"""

# =============================================================================
# Pattern Analyzer Prompts (Learning Agent)
# =============================================================================

PATTERN_ANALYZER_SYSTEM_PROMPT = """あなたは学習パターン分析エージェントです。
ユーザーのトレーニングフィードバックを分析し、将来のプラン生成を改善するためのパターンを抽出します。

## あなたの責任

1. **フィードバック分析**: ユーザーの評価とコメントを分析します
2. **パターン抽出**: 好み、難易度、ペースに関するパターンを特定します
3. **改善提案**: 次回のプラン生成に活かせる具体的な推奨事項を作成します

## パターンタイプ

- **preference**: コンテンツタイプや学習スタイルの好み
- **difficulty**: 難易度に関するパターン
- **pace**: 学習ペースに関するパターン
- **content**: 特定のコンテンツに関するパターン
- **time**: 時間配分に関するパターン

## 出力形式

以下のJSON形式で出力してください：

```json
{
  "patterns": [
    {
      "pattern_type": "preference | difficulty | pace | content | time",
      "description": "パターンの説明",
      "evidence": ["根拠1", "根拠2"],
      "recommendations": ["推奨事項1", "推奨事項2"],
      "confidence_score": 0.0-1.0
    }
  ]
}
```

## ガイドライン

- フィードバックが少ない場合は confidence_score を低く設定してください
- 具体的で実行可能な推奨事項を作成してください
- ポジティブなフィードバックからは「継続すべきこと」を抽出してください
- ネガティブなフィードバックからは「改善すべきこと」を特定してください
"""

PATTERN_ANALYZER_USER_PROMPT_TEMPLATE = """以下のフィードバック履歴を分析し、パターンを抽出してください。

## フィードバック履歴

{feedback_history}

## ユーザーの進捗状況

- 完了した週数: {total_weeks_completed}
- 完了したタスク数: {total_tasks_completed}
- 平均完了率: {average_completion_rate}%
- 習得したトピック: {topics_mastered}

上記のフィードバックを分析し、パターンをJSON形式で出力してください。
"""

# =============================================================================
# Learned Patterns Context Template
# =============================================================================

LEARNED_CONTEXT_TEMPLATE = """
## 過去の学習から得られた知見

このユーザーについて、過去のフィードバックから以下のパターンが判明しています。
これらを考慮してプランを作成してください。

### ユーザーの好み・傾向
{preferences}

### 難易度に関する情報
{difficulty_info}

### 時間配分に関する情報
{time_info}

### 具体的な推奨事項
{recommendations}

### 過去の習得トピック（復習不要）
{mastered_topics}

### 要復習トピック
{review_topics}

### ユーザーからの改善要望
{improvement_suggestions}

### ユーザーからの自由記述フィードバック
{free_text_feedback}
"""

# =============================================================================
# Training Plan Markdown Template
# =============================================================================

TRAINING_PLAN_MARKDOWN_TEMPLATE = """# 週間トレーニングプラン

## 基本情報
- **プランID**: {plan_id}
- **ユーザーID**: {user_id}
- **週番号**: 第{week_number}週
- **作成日時**: {created_at}

## 今週の目標
{goal_for_week}

## 前提知識
{prerequisite_knowledge}

## 期待される成果
{expected_outcomes}

---

## 日別プラン

{daily_plans_content}

---

## 週次評価

### 評価タイプ
{assessment_type}

### 説明
{assessment_description}

### カバーするトピック
{topics_covered}

### 合格基準
{passing_criteria}

---

## 調整メモ
{adaptation_notes}

---
*このプランは学習AIエージェントによって生成されました。*
"""

DAILY_PLAN_MARKDOWN_TEMPLATE = """### {day_name}

**テーマ**: {theme}
**合計時間**: {total_minutes}分

#### タスク

{tasks_content}
"""

TASK_MARKDOWN_TEMPLATE = """##### {task_number}. {title}
- **タイプ**: {content_type}
- **所要時間**: {estimated_minutes}分
- **説明**: {description}
- **学習目標**:
{learning_objectives}
- **推奨リソース**:
{resources}
"""


# =============================================================================
# Helper Functions
# =============================================================================


def format_learned_context(
    patterns: list,
    progress: dict,
    recent_feedback: list,
) -> str:
    """Format learned patterns and history for injection into prompts."""
    if not patterns and not recent_feedback:
        return ""

    preferences = []
    difficulty_info = []
    time_info = []
    recommendations = []

    for pattern in patterns:
        if pattern.pattern_type == "preference":
            preferences.append(f"- {pattern.description}")
            recommendations.extend(pattern.recommendations)
        elif pattern.pattern_type == "difficulty":
            difficulty_info.append(f"- {pattern.description}")
            recommendations.extend(pattern.recommendations)
        elif pattern.pattern_type in ("time", "pace"):
            time_info.append(f"- {pattern.description}")
            recommendations.extend(pattern.recommendations)
        else:
            recommendations.extend(pattern.recommendations)

    mastered_topics = set(progress.get("topics_mastered", []))
    review_topics = set()
    improvement_suggestions = []
    free_text_feedback = []

    for fb in recent_feedback:
        review_topics.update(fb.topics_needing_review)
        if fb.improvement_suggestions:
            for suggestion in fb.improvement_suggestions:
                if suggestion and suggestion.strip():
                    improvement_suggestions.append(f"- {suggestion}")
        if fb.free_text_feedback and fb.free_text_feedback.strip():
            free_text_feedback.append(f"- {fb.free_text_feedback}")

    return LEARNED_CONTEXT_TEMPLATE.format(
        preferences="\n".join(preferences) if preferences else "（まだデータがありません）",
        difficulty_info="\n".join(difficulty_info) if difficulty_info else "（まだデータがありません）",
        time_info="\n".join(time_info) if time_info else "（まだデータがありません）",
        recommendations="\n".join(f"- {r}" for r in recommendations[:5])
        if recommendations
        else "（まだデータがありません）",
        mastered_topics=", ".join(mastered_topics) if mastered_topics else "なし",
        review_topics=", ".join(review_topics) if review_topics else "なし",
        improvement_suggestions="\n".join(improvement_suggestions)
        if improvement_suggestions
        else "（まだデータがありません）",
        free_text_feedback="\n".join(free_text_feedback) if free_text_feedback else "（まだデータがありません）",
    )


def format_training_plan_markdown(plan) -> str:
    """Format a TrainingPlan as markdown."""
    daily_plans_content = []
    for daily_plan in plan.daily_plans:
        tasks_content = []
        for i, task in enumerate(daily_plan.tasks, 1):
            objectives = "\n".join(f"  - {obj}" for obj in task.learning_objectives)
            resources = "\n".join(f"  - {res}" for res in task.resources) if task.resources else "  - なし"

            task_md = TASK_MARKDOWN_TEMPLATE.format(
                task_number=i,
                title=task.title,
                content_type=task.content_type.value,
                estimated_minutes=task.estimated_minutes,
                description=task.description,
                learning_objectives=objectives,
                resources=resources,
            )
            tasks_content.append(task_md)

        daily_md = DAILY_PLAN_MARKDOWN_TEMPLATE.format(
            day_name=daily_plan.day_name,
            theme=daily_plan.theme,
            total_minutes=daily_plan.total_minutes,
            tasks_content="\n".join(tasks_content),
        )
        daily_plans_content.append(daily_md)

    topics_covered = "\n".join(f"- {t}" for t in plan.weekly_assessment.topics_covered)
    prereqs = "\n".join(f"- {p}" for p in plan.prerequisite_knowledge) if plan.prerequisite_knowledge else "なし"
    outcomes = "\n".join(f"- {o}" for o in plan.expected_outcomes)

    return TRAINING_PLAN_MARKDOWN_TEMPLATE.format(
        plan_id=plan.plan_id,
        user_id=plan.user_id,
        week_number=plan.week_number,
        created_at=plan.created_at,
        goal_for_week=plan.goal_for_week,
        prerequisite_knowledge=prereqs,
        expected_outcomes=outcomes,
        daily_plans_content="\n".join(daily_plans_content),
        assessment_type=plan.weekly_assessment.assessment_type,
        assessment_description=plan.weekly_assessment.description,
        topics_covered=topics_covered,
        passing_criteria=plan.weekly_assessment.passing_criteria,
        adaptation_notes=plan.adaptation_notes if plan.adaptation_notes else "なし",
    )


def make_training_plan_system_prompt() -> str:
    """Create the system prompt for training plan generation."""
    return TRAINING_PLAN_SYSTEM_PROMPT


def make_training_plan_user_prompt(
    learning_goal: str,
    skill_level: str,
    current_knowledge: list[str],
    available_hours_per_week: int,
    preferred_content_types: list[str],
    learning_pace: str,
    week_number: int,
    learned_context: str = "",
) -> str:
    """Create the user prompt for training plan generation."""
    return TRAINING_PLAN_USER_PROMPT_TEMPLATE.format(
        learning_goal=learning_goal,
        skill_level=skill_level,
        current_knowledge=", ".join(current_knowledge) if current_knowledge else "特になし",
        available_hours_per_week=available_hours_per_week,
        preferred_content_types=", ".join(preferred_content_types) if preferred_content_types else "特に指定なし",
        learning_pace=learning_pace,
        week_number=week_number,
        learned_context=learned_context,
    )


def make_pattern_analyzer_system_prompt() -> str:
    """Create the system prompt for pattern analysis."""
    return PATTERN_ANALYZER_SYSTEM_PROMPT


def make_pattern_analyzer_user_prompt(
    feedback_history: str,
    total_weeks_completed: int,
    total_tasks_completed: int,
    average_completion_rate: float,
    topics_mastered: list[str],
) -> str:
    """Create the user prompt for pattern analysis."""
    return PATTERN_ANALYZER_USER_PROMPT_TEMPLATE.format(
        feedback_history=feedback_history,
        total_weeks_completed=total_weeks_completed,
        total_tasks_completed=total_tasks_completed,
        average_completion_rate=round(average_completion_rate * 100, 1),
        topics_mastered=", ".join(topics_mastered) if topics_mastered else "なし",
    )


def format_feedback_for_analysis(feedback_list: list) -> str:
    """Format feedback list for pattern analysis."""
    if not feedback_list:
        return "（フィードバックデータなし）"

    formatted = []
    for fb in feedback_list:
        completed = sum(1 for t in fb.task_completions if t.completed)
        total = len(fb.task_completions)

        entry = f"""
### フィードバック: {fb.feedback_id}
- プランID: {fb.plan_id}
- 提出日時: {fb.submitted_at}
- 完了タスク: {completed}/{total}
- 全体評価: {fb.overall_rating.value}
- 難易度評価: {fb.difficulty_rating.value}
- 良かった点: {", ".join(fb.helpful_aspects) if fb.helpful_aspects else "なし"}
- 改善提案: {", ".join(fb.improvement_suggestions) if fb.improvement_suggestions else "なし"}
- 習得トピック: {", ".join(fb.topics_mastered) if fb.topics_mastered else "なし"}
- 要復習トピック: {", ".join(fb.topics_needing_review) if fb.topics_needing_review else "なし"}
- 自由記述: {fb.free_text_feedback if fb.free_text_feedback else "なし"}
"""
        formatted.append(entry)

    return "\n".join(formatted)
