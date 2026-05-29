"""Pydantic models for the Hierarchical Personalized Learning Platform."""

from enum import StrEnum
from typing import Annotated, Sequence

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, ConfigDict, Field
from typing_extensions import TypedDict


class FrozenModel(BaseModel):
    """
    Base model with common configuration for all learning platform models.

    Configuration:
    - validate_assignment: Validates data on attribute assignment
    - frozen: Makes instances immutable after creation
    - extra: Ignores extra fields not defined in the model
    """

    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True,
        extra="ignore",
    )


class SkillLevel(StrEnum):
    """Skill level classification."""

    BEGINNER = "beginner"
    ELEMENTARY = "elementary"
    INTERMEDIATE = "intermediate"
    UPPER_INTERMEDIATE = "upper_intermediate"
    ADVANCED = "advanced"


class ContentType(StrEnum):
    """Types of learning content."""

    VIDEO = "video"
    ARTICLE = "article"
    INTERACTIVE = "interactive"
    EXERCISE = "exercise"
    PROJECT = "project"


class QuestionType(StrEnum):
    """Types of quiz questions."""

    MULTIPLE_CHOICE = "multiple_choice"
    TRUE_FALSE = "true_false"
    SHORT_ANSWER = "short_answer"
    CODING = "coding"


class LearningModuleCategory(StrEnum):
    """Categories of learning modules."""

    FUNDAMENTALS = "fundamentals"
    THEORY = "theory"
    PRACTICAL = "practical"
    ADVANCED_TOPICS = "advanced_topics"
    PROJECT = "project"


class LearningModule(FrozenModel):
    """A learning module in the roadmap."""

    module_id: str = Field(..., description="Unique identifier for the module")
    name: str = Field(..., description="Name of the learning module")
    category: LearningModuleCategory = Field(..., description="Category of the module")
    description: str = Field(..., description="Brief description of what will be learned")
    prerequisites: list[str] = Field(default_factory=list, description="Module IDs that should be completed first")
    estimated_hours: int = Field(..., description="Estimated hours to complete")
    target_competencies: list[str] = Field(..., description="Skills/competencies to be acquired")


class LearningRoadmap(FrozenModel):
    """Strategic learning roadmap."""

    goal_summary: str = Field(..., description="Summary of the learning goal")
    target_level: SkillLevel = Field(..., description="Target skill level to achieve")
    current_level: SkillLevel = Field(..., description="Current assessed skill level")
    total_duration_weeks: int = Field(..., description="Total estimated duration in weeks")
    modules: list[LearningModule] = Field(..., description="Ordered list of learning modules")
    milestones: list[str] = Field(..., description="Key milestones to track progress")
    success_criteria: list[str] = Field(..., description="Criteria to determine goal achievement")


class StrategyOutput(FrozenModel):
    """Output from the Strategy Agent."""

    learning_domain: str = Field(..., description="The domain of learning (e.g., Data Analysis, Programming)")
    roadmap: LearningRoadmap = Field(..., description="The complete learning roadmap")
    recommended_study_hours_per_week: int = Field(..., description="Recommended study hours per week")
    learning_style_notes: str = Field(..., description="Notes on recommended learning approach")


class DailyTask(FrozenModel):
    """A daily learning task."""

    task_id: str = Field(..., description="Unique identifier for the task")
    title: str = Field(..., description="Title of the task")
    description: str = Field(..., description="Detailed description")
    content_type: ContentType = Field(..., description="Type of content")
    estimated_minutes: int = Field(..., description="Estimated time in minutes")
    learning_objectives: list[str] = Field(..., description="What the learner will achieve")


class WeeklyPlan(FrozenModel):
    """A weekly learning plan."""

    week_number: int = Field(..., description="Week number in the curriculum")
    module_id: str = Field(..., description="Associated module ID")
    theme: str = Field(..., description="Theme for the week")
    learning_goals: list[str] = Field(..., description="Goals for this week")
    daily_tasks: dict[str, list[DailyTask]] = Field(
        default_factory=dict, description="Tasks organized by day (day1, day2, etc.)"
    )
    weekly_assessment: str = Field(..., description="Description of weekly assessment")


class TacticsOutput(FrozenModel):
    """Output from the Tactics Agent."""

    curriculum_summary: str = Field(..., description="Summary of the curriculum")
    weekly_plans: list[WeeklyPlan] = Field(..., description="Detailed weekly plans")
    assessment_strategy: str = Field(..., description="Overall assessment strategy")
    adaptation_notes: str = Field(..., description="Notes on how curriculum may adapt")


class LearningContent(FrozenModel):
    """Learning content provided by the content agent."""

    content_id: str = Field(..., description="Unique identifier for the content")
    task_id: str = Field(..., description="Associated task ID")
    title: str = Field(..., description="Title of the content")
    content_type: ContentType = Field(..., description="Type of content")
    content_body: str = Field(..., description="The actual learning content")
    key_concepts: list[str] = Field(..., description="Key concepts covered")
    resources: list[str] = Field(default_factory=list, description="Additional resources/links")


class QuizQuestion(FrozenModel):
    """A quiz question for assessment."""

    question_id: str = Field(..., description="Unique identifier for the question")
    question_type: QuestionType = Field(..., description="Type of question")
    question_text: str = Field(..., description="The question text")
    options: list[str] = Field(default_factory=list, description="Options for multiple choice")
    correct_answer: str = Field(..., description="The correct answer")
    explanation: str = Field(..., description="Explanation of the correct answer")
    difficulty: SkillLevel = Field(..., description="Difficulty level of the question")
    related_concepts: list[str] = Field(..., description="Concepts this question tests")


class Quiz(FrozenModel):
    """A quiz generated by the quiz agent."""

    quiz_id: str = Field(..., description="Unique identifier for the quiz")
    task_id: str = Field(..., description="Associated task ID")
    title: str = Field(..., description="Title of the quiz")
    questions: list[QuizQuestion] = Field(..., description="List of questions")
    passing_score: int = Field(..., description="Minimum score to pass (percentage)")
    time_limit_minutes: int = Field(default=0, description="Time limit in minutes (0 = no limit)")


class FeedbackItem(FrozenModel):
    """Feedback on learner's answer."""

    question_id: str = Field(..., description="Question being addressed")
    is_correct: bool = Field(..., description="Whether the answer was correct")
    learner_answer: str = Field(..., description="The learner's answer")
    feedback_text: str = Field(..., description="Detailed feedback")
    improvement_suggestion: str = Field(..., description="Suggestion for improvement")
    related_content: list[str] = Field(default_factory=list, description="Content to review")


class LearnerFeedback(FrozenModel):
    """Complete feedback from the feedback agent."""

    feedback_id: str = Field(..., description="Unique identifier for the feedback")
    quiz_id: str = Field(..., description="Associated quiz ID")
    score: int = Field(..., description="Score achieved (percentage)")
    passed: bool = Field(..., description="Whether the quiz was passed")
    items: list[FeedbackItem] = Field(..., description="Feedback for each question")
    overall_feedback: str = Field(..., description="Overall feedback summary")
    strengths: list[str] = Field(..., description="Areas of strength")
    areas_for_improvement: list[str] = Field(..., description="Areas needing improvement")
    recommended_next_steps: list[str] = Field(..., description="Recommended next steps")


class ProgressMetrics(FrozenModel):
    """Progress metrics from the reflection agent for quality evaluation."""

    modules_completed: int = Field(..., description="Number of modules completed")
    total_modules: int = Field(..., description="Total number of modules")
    current_week: int = Field(..., description="Current week in the curriculum")
    tasks_completed_this_week: int = Field(..., description="Tasks completed this week")
    total_tasks_this_week: int = Field(..., description="Total tasks for this week")
    average_quiz_score: float = Field(..., description="Average quiz score (percentage)")
    study_hours_logged: float = Field(..., description="Total study hours logged")
    streak_days: int = Field(..., description="Consecutive days of study")
    competencies_acquired: list[str] = Field(..., description="Competencies acquired so far")
    on_track: bool = Field(..., description="Whether learner is on track with the plan")


class ProgressReport(FrozenModel):
    """
    Progress report from the Reflection Layer agent.

    This model captures the evaluation output from the reflection layer,
    including quality assessment and recommendations for plan adjustments.
    When curriculum_adjustment_needed is True, the reflection layer is
    signaling that upper layers (strategy/tactics) should revise their plans.
    """

    report_id: str = Field(..., description="Unique identifier for the report")
    metrics: ProgressMetrics = Field(..., description="Current progress metrics")
    progress_summary: str = Field(..., description="Summary of progress")
    achievements: list[str] = Field(..., description="Recent achievements")
    recommendations: list[str] = Field(..., description="Recommendations for improvement")
    curriculum_adjustment_needed: bool = Field(..., description="Whether curriculum adjustment is needed")
    adjustment_reason: str = Field(default="", description="Reason for adjustment if needed")


class LearnerProfile(FrozenModel):
    """Profile of the learner."""

    learner_id: str = Field(..., description="Unique identifier for the learner")
    learning_goal: str = Field(..., description="The learner's stated goal")
    current_knowledge: list[str] = Field(default_factory=list, description="Current knowledge areas")
    available_hours_per_week: int = Field(..., description="Available study hours per week")
    preferred_content_types: list[ContentType] = Field(default_factory=list, description="Preferred content types")
    target_duration_weeks: int = Field(default=12, description="Target duration in weeks")


class LearningSession(FrozenModel):
    """A learning session containing content, quiz, and feedback."""

    session_id: str = Field(..., description="Unique identifier for the session")
    task_id: str = Field(..., description="Associated task ID")
    content: LearningContent = Field(..., description="Learning content for the session")
    quiz: Quiz = Field(..., description="Quiz for the session")
    feedback: LearnerFeedback | None = Field(default=None, description="Feedback if quiz taken")


class PersonalizedLearningPlan(FrozenModel):
    """Complete personalized learning plan."""

    plan_id: str = Field(..., description="Unique identifier for the plan")
    learner_profile: LearnerProfile = Field(..., description="Learner profile")
    strategy: StrategyOutput = Field(..., description="Strategic learning plan")
    curriculum: TacticsOutput = Field(..., description="Detailed curriculum")
    first_week_sessions: list[LearningSession] = Field(..., description="Sessions for the first week")
    progress_report: ProgressReport = Field(..., description="Initial progress report")

    def to_markdown(self) -> str:
        """Convert the learning plan to markdown format."""
        lines = [
            "# パーソナライズ学習プラン",
            "",
            "## 学習者プロフィール",
            f"- **学習目標**: {self.learner_profile.learning_goal}",
            f"- **週あたり学習時間**: {self.learner_profile.available_hours_per_week}時間",
            f"- **目標期間**: {self.learner_profile.target_duration_weeks}週間",
            "",
            "## 戦略概要",
            f"- **学習ドメイン**: {self.strategy.learning_domain}",
            f"- **現在レベル**: {self.strategy.roadmap.current_level.value}",
            f"- **目標レベル**: {self.strategy.roadmap.target_level.value}",
            f"- **推奨学習時間**: 週{self.strategy.recommended_study_hours_per_week}時間",
            "",
            "## 学習ロードマップ",
            "",
            "### ゴールサマリー",
            self.strategy.roadmap.goal_summary,
            "",
            "### マイルストーン",
        ]

        for i, milestone in enumerate(self.strategy.roadmap.milestones, 1):
            lines.append(f"{i}. {milestone}")

        lines.extend(["", "## 学習モジュール"])
        for m in self.strategy.roadmap.modules:
            lines.extend(
                [
                    f"### {m.module_id}: {m.name}",
                    f"- **カテゴリ**: {m.category.value}",
                    f"- **説明**: {m.description}",
                    f"- **推定時間**: {m.estimated_hours}時間",
                    f"- **習得スキル**: {', '.join(m.target_competencies)}",
                    "",
                ]
            )

        lines.extend(
            [
                "## カリキュラム詳細",
                "",
                "### カリキュラム概要",
                self.curriculum.curriculum_summary,
                "",
                "### 評価戦略",
                self.curriculum.assessment_strategy,
                "",
            ]
        )

        for week in self.curriculum.weekly_plans[:2]:
            lines.extend(
                [
                    f"### 第{week.week_number}週: {week.theme}",
                    "**学習目標**:",
                ]
            )
            for goal in week.learning_goals:
                lines.append(f"- {goal}")

            lines.append("")
            lines.append("**日別タスク**:")
            for day, tasks in week.daily_tasks.items():
                task_names = ", ".join(t.title for t in tasks)
                lines.append(f"  - **{day}**: {task_names}")

            lines.extend(
                [
                    "",
                    f"**週次評価**: {week.weekly_assessment}",
                    "",
                ]
            )

        lines.append("## 今週の学習セッション")
        for session in self.first_week_sessions[:3]:
            lines.extend(
                [
                    "",
                    f"### {session.content.title}",
                    f"- **コンテンツタイプ**: {session.content.content_type.value}",
                    f"- **キーコンセプト**: {', '.join(session.content.key_concepts)}",
                    "",
                    f"**クイズ**: {session.quiz.title} ({len(session.quiz.questions)}問)",
                    "",
                ]
            )

        track_status = "順調" if self.progress_report.metrics.on_track else "調整が必要"
        lines.extend(
            [
                "## 進捗レポート",
                f"- **進捗状況**: {self.progress_report.progress_summary}",
                f"- **トラック状況**: {track_status}",
                "",
                "### 推奨事項",
            ]
        )
        for rec in self.progress_report.recommendations:
            lines.append(f"- {rec}")

        return "\n".join(lines)


class HierarchicalAgentState(TypedDict):
    """State for the hierarchical personalized learning agent system."""

    learner_profile: LearnerProfile
    strategy_output: StrategyOutput | None
    tactics_output: TacticsOutput | None
    learning_sessions: list[LearningSession]
    progress_report: ProgressReport | None
    current_week: int
    current_day: str
    current_task_index: int
    messages: Annotated[Sequence[BaseMessage], add_messages]
