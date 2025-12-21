"""
Pydantic models for the Learning AI Agent - Training Plan Generator.

This module defines data models for a learning AI agent that:
- Generates personalized 1-week training plans
- Stores user memory (profile, history, feedback) in JSON files
- Learns from past interactions to improve future recommendations

Memory Structure:
- UserMemory: Main container storing all user-related data
- UserProfile: User's learning goals, knowledge, preferences
- TrainingPlan: Weekly training plan with daily tasks
- TrainingFeedback: User feedback on completed training
- LearnedPattern: Patterns extracted from feedback for improvement
"""

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# =============================================================================
# Base Model Configuration
# =============================================================================


class FrozenModel(BaseModel):
    """Base model with immutable configuration."""

    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True,
        extra="ignore",
    )


class MutableModel(BaseModel):
    """Base model for mutable data structures like memory stores."""

    model_config = ConfigDict(
        validate_assignment=True,
        extra="ignore",
    )


# =============================================================================
# Enums
# =============================================================================


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
    EXERCISE = "exercise"
    PROJECT = "project"
    QUIZ = "quiz"


class DifficultyRating(StrEnum):
    """User's rating of training difficulty."""

    TOO_EASY = "too_easy"
    EASY = "easy"
    JUST_RIGHT = "just_right"
    CHALLENGING = "challenging"
    TOO_HARD = "too_hard"


class FeedbackRating(StrEnum):
    """Overall feedback rating."""

    EXCELLENT = "excellent"
    GOOD = "good"
    NEUTRAL = "neutral"
    POOR = "poor"
    VERY_POOR = "very_poor"


# =============================================================================
# User Profile Models
# =============================================================================


class UserProfile(FrozenModel):
    """User's learning profile."""

    user_id: str = Field(..., description="Unique user identifier")
    learning_goal: str = Field(..., description="User's primary learning goal")
    current_knowledge: list[str] = Field(default_factory=list, description="Topics the user already knows")
    skill_level: SkillLevel = Field(default=SkillLevel.BEGINNER, description="Current skill level")
    available_hours_per_week: int = Field(default=10, description="Hours available for learning per week")
    preferred_content_types: list[ContentType] = Field(
        default_factory=list, description="Preferred learning content types"
    )
    learning_pace: str = Field(default="moderate", description="Preferred learning pace (slow/moderate/fast)")


# =============================================================================
# Training Plan Models
# =============================================================================


class DailyTask(FrozenModel):
    """A single learning task for a day."""

    task_id: str = Field(..., description="Unique task identifier")
    title: str = Field(..., description="Task title")
    description: str = Field(..., description="Detailed task description")
    content_type: ContentType = Field(..., description="Type of content")
    estimated_minutes: int = Field(..., description="Estimated time in minutes")
    learning_objectives: list[str] = Field(..., description="What the user will learn")
    resources: list[str] = Field(default_factory=list, description="Recommended resources")


class DailyPlan(FrozenModel):
    """Plan for a single day."""

    day_number: int = Field(..., description="Day number (1-7)")
    day_name: str = Field(..., description="Day name (e.g., 'Day 1 - Monday')")
    theme: str = Field(..., description="Theme for the day")
    tasks: list[DailyTask] = Field(..., description="Tasks for the day")
    total_minutes: int = Field(..., description="Total estimated minutes")


class WeeklyAssessment(FrozenModel):
    """Weekly assessment details."""

    assessment_type: str = Field(..., description="Type of assessment")
    description: str = Field(..., description="Assessment description")
    topics_covered: list[str] = Field(..., description="Topics to be assessed")
    passing_criteria: str = Field(..., description="Criteria for passing")


class TrainingPlan(FrozenModel):
    """A complete 1-week training plan."""

    plan_id: str = Field(..., description="Unique plan identifier")
    user_id: str = Field(..., description="User this plan is for")
    week_number: int = Field(..., description="Week number in the learning journey")
    created_at: str = Field(..., description="When the plan was created")
    goal_for_week: str = Field(..., description="Primary goal for this week")
    prerequisite_knowledge: list[str] = Field(default_factory=list, description="Required prerequisite knowledge")
    daily_plans: list[DailyPlan] = Field(..., description="Daily plans for the week")
    weekly_assessment: WeeklyAssessment = Field(..., description="End of week assessment")
    expected_outcomes: list[str] = Field(..., description="Expected learning outcomes")
    adaptation_notes: str = Field(default="", description="Notes on how this plan was adapted based on memory")


# =============================================================================
# Feedback Models
# =============================================================================


class TaskCompletion(FrozenModel):
    """Completion status of a single task."""

    task_id: str = Field(..., description="Task identifier")
    completed: bool = Field(..., description="Whether task was completed")
    actual_minutes: int = Field(default=0, description="Actual time spent in minutes")
    notes: str = Field(default="", description="User notes on the task")


class TrainingFeedback(FrozenModel):
    """User feedback on a completed training plan."""

    feedback_id: str = Field(..., description="Unique feedback identifier")
    plan_id: str = Field(..., description="Plan this feedback is for")
    user_id: str = Field(..., description="User who provided feedback")
    submitted_at: str = Field(..., description="When feedback was submitted")
    task_completions: list[TaskCompletion] = Field(..., description="Completion status of each task")
    overall_rating: FeedbackRating = Field(..., description="Overall rating")
    difficulty_rating: DifficultyRating = Field(..., description="Difficulty rating")
    helpful_aspects: list[str] = Field(default_factory=list, description="What was helpful")
    improvement_suggestions: list[str] = Field(default_factory=list, description="Suggestions for improvement")
    topics_mastered: list[str] = Field(default_factory=list, description="Topics the user feels they mastered")
    topics_needing_review: list[str] = Field(default_factory=list, description="Topics needing more practice")
    free_text_feedback: str = Field(default="", description="Additional free-text feedback")


# =============================================================================
# Learned Pattern Models
# =============================================================================


class LearnedPattern(FrozenModel):
    """A pattern learned from analyzing user feedback."""

    pattern_id: str = Field(..., description="Unique pattern identifier")
    pattern_type: str = Field(..., description="Type of pattern (preference/difficulty/pace/content)")
    description: str = Field(..., description="Description of the pattern")
    evidence: list[str] = Field(..., description="Evidence from feedback supporting this pattern")
    recommendations: list[str] = Field(..., description="Recommendations based on this pattern")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence in this pattern")
    created_at: str = Field(..., description="When the pattern was identified")
    source_feedback_ids: list[str] = Field(..., description="Feedback IDs this pattern is based on")


# =============================================================================
# Memory Models
# =============================================================================


class TrainingRecord(FrozenModel):
    """Record of a training plan and its feedback."""

    plan: TrainingPlan = Field(..., description="The training plan")
    feedback: TrainingFeedback | None = Field(default=None, description="Feedback if provided")


class LearningProgress(FrozenModel):
    """User's overall learning progress."""

    total_weeks_completed: int = Field(default=0, description="Total weeks of training completed")
    total_tasks_completed: int = Field(default=0, description="Total tasks completed")
    total_hours_spent: float = Field(default=0.0, description="Total hours spent learning")
    topics_mastered: list[str] = Field(default_factory=list, description="All topics mastered")
    current_skill_level: SkillLevel = Field(default=SkillLevel.BEGINNER, description="Current assessed skill level")
    streak_weeks: int = Field(default=0, description="Consecutive weeks of training")
    average_completion_rate: float = Field(default=0.0, description="Average task completion rate")


class UserMemory(MutableModel):
    """
    Complete memory store for a user.

    This is the main container that stores all user-related data:
    - Profile: User's learning preferences and goals
    - Training history: Past training plans and feedback
    - Learned patterns: Patterns extracted from feedback
    - Progress: Overall learning progress metrics
    """

    user_id: str = Field(..., description="User identifier")
    created_at: str = Field(..., description="When memory was created")
    updated_at: str = Field(..., description="When memory was last updated")
    profile: UserProfile = Field(..., description="User profile")
    training_history: list[TrainingRecord] = Field(
        default_factory=list, description="History of training plans and feedback"
    )
    learned_patterns: list[LearnedPattern] = Field(default_factory=list, description="Patterns learned from feedback")
    progress: LearningProgress = Field(
        default_factory=lambda: LearningProgress(), description="Overall learning progress"
    )

    def add_training_plan(self, plan: TrainingPlan) -> None:
        """Add a new training plan to history."""
        record = TrainingRecord(plan=plan, feedback=None)
        self.training_history.append(record)
        self.updated_at = datetime.now().isoformat()

    def add_feedback(self, feedback: TrainingFeedback) -> None:
        """Add feedback for a training plan."""
        for i, record in enumerate(self.training_history):
            if record.plan.plan_id == feedback.plan_id:
                # TrainingRecord is frozen, so create new record with feedback
                updated_record = TrainingRecord(plan=record.plan, feedback=feedback)
                self.training_history[i] = updated_record
                break
        self._update_progress(feedback)
        self.updated_at = datetime.now().isoformat()

    def add_learned_pattern(self, pattern: LearnedPattern) -> None:
        """Add a learned pattern."""
        self.learned_patterns.append(pattern)
        self.updated_at = datetime.now().isoformat()

    def get_recent_feedback(self, limit: int = 5) -> list[TrainingFeedback]:
        """Get recent feedback entries."""
        feedbacks = [r.feedback for r in self.training_history if r.feedback is not None]
        return feedbacks[-limit:]

    def get_pending_plans(self) -> list[TrainingPlan]:
        """Get plans without feedback."""
        return [r.plan for r in self.training_history if r.feedback is None]

    def get_latest_plan(self) -> TrainingPlan | None:
        """Get the most recent training plan."""
        if not self.training_history:
            return None
        return self.training_history[-1].plan

    def get_patterns_for_prompt(self) -> list[LearnedPattern]:
        """Get high-confidence patterns for prompt injection."""
        return [p for p in self.learned_patterns if p.confidence_score >= 0.6]

    def _update_progress(self, feedback: TrainingFeedback) -> None:
        """Update progress based on new feedback."""
        completed_tasks = sum(1 for t in feedback.task_completions if t.completed)
        total_minutes = sum(t.actual_minutes for t in feedback.task_completions)

        new_weeks = self.progress.total_weeks_completed + 1
        new_tasks = self.progress.total_tasks_completed + completed_tasks
        new_hours = self.progress.total_hours_spent + (total_minutes / 60)
        new_mastered = list(set(self.progress.topics_mastered + feedback.topics_mastered))

        total_task_count = len(feedback.task_completions)
        if total_task_count > 0:
            new_rate = completed_tasks / total_task_count
            if self.progress.total_weeks_completed > 0:
                new_avg_rate = (
                    self.progress.average_completion_rate * self.progress.total_weeks_completed + new_rate
                ) / new_weeks
            else:
                new_avg_rate = new_rate
        else:
            new_avg_rate = self.progress.average_completion_rate

        new_streak = self.progress.streak_weeks + 1 if completed_tasks > 0 else 0

        self.progress = LearningProgress(
            total_weeks_completed=new_weeks,
            total_tasks_completed=new_tasks,
            total_hours_spent=round(new_hours, 1),
            topics_mastered=new_mastered,
            current_skill_level=self.progress.current_skill_level,
            streak_weeks=new_streak,
            average_completion_rate=round(new_avg_rate, 2),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "UserMemory":
        """Create from dictionary."""
        return cls.model_validate(data)


# =============================================================================
# LLM Response Models (for structured output)
# =============================================================================


class DailyTaskResponse(BaseModel):
    """LLM response schema for a daily task."""

    task_id: str = Field(default="", description="Unique task identifier")
    title: str = Field(..., description="Task title")
    description: str = Field(..., description="Detailed task description")
    content_type: str = Field(default="article", description="Type of content")
    estimated_minutes: int = Field(default=30, description="Estimated time in minutes")
    learning_objectives: list[str] = Field(default_factory=list, description="What the user will learn")
    resources: list[str] = Field(default_factory=list, description="Recommended resources")


class DailyPlanResponse(BaseModel):
    """LLM response schema for a daily plan."""

    day_number: int = Field(..., description="Day number (1-7)")
    day_name: str = Field(default="", description="Day name")
    theme: str = Field(default="", description="Theme for the day")
    tasks: list[DailyTaskResponse] = Field(default_factory=list, description="Tasks for the day")
    total_minutes: int = Field(default=0, description="Total estimated minutes")


class WeeklyAssessmentResponse(BaseModel):
    """LLM response schema for weekly assessment."""

    assessment_type: str = Field(default="Quiz", description="Type of assessment")
    description: str = Field(default="", description="Assessment description")
    topics_covered: list[str] = Field(default_factory=list, description="Topics to be assessed")
    passing_criteria: str = Field(default="70% correct", description="Passing criteria")


class TrainingPlanResponse(BaseModel):
    """LLM response schema for training plan generation."""

    goal_for_week: str = Field(..., description="Primary goal for this week")
    prerequisite_knowledge: list[str] = Field(default_factory=list, description="Required prerequisite knowledge")
    daily_plans: list[DailyPlanResponse] = Field(..., description="Daily plans for the week")
    weekly_assessment: WeeklyAssessmentResponse = Field(
        default_factory=WeeklyAssessmentResponse, description="End of week assessment"
    )
    expected_outcomes: list[str] = Field(default_factory=list, description="Expected learning outcomes")
    adaptation_notes: str = Field(default="", description="Notes on how this plan was adapted")


class LearnedPatternResponse(BaseModel):
    """LLM response schema for a learned pattern."""

    pattern_type: str = Field(..., description="Type of pattern")
    description: str = Field(..., description="Description of the pattern")
    evidence: list[str] = Field(default_factory=list, description="Evidence from feedback")
    recommendations: list[str] = Field(default_factory=list, description="Recommendations based on this pattern")
    confidence_score: float = Field(default=0.5, ge=0.0, le=1.0, description="Confidence in this pattern")


class PatternAnalysisResponse(BaseModel):
    """LLM response schema for pattern analysis."""

    patterns: list[LearnedPatternResponse] = Field(default_factory=list, description="Extracted patterns from feedback")


# =============================================================================
# Agent State Model (for LangGraph if needed)
# =============================================================================


class AgentState(MutableModel):
    """State for the learning agent workflow."""

    user_memory: UserMemory | None = Field(default=None, description="User's memory")
    current_plan: TrainingPlan | None = Field(default=None, description="Currently generated plan")
    current_feedback: TrainingFeedback | None = Field(default=None, description="Current feedback being processed")
    learned_context: str = Field(default="", description="Formatted learned patterns for prompt")
    error: str | None = Field(default=None, description="Error message if any")
