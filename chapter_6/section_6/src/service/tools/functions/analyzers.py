"""Data analysis functions using Polars for statistical computations."""

from dataclasses import dataclass

import polars as pl


@dataclass
class SubjectStats:
    """Statistics for a single subject."""

    mean: float
    min: int
    max: int
    std: float = 0.0


@dataclass
class ScoreAnalysis:
    """Analysis results for test scores."""

    subject_stats: dict[str, SubjectStats]
    overall_mean: float
    record_count: int
    unique_students: int
    unique_quarters: int


@dataclass
class GradeDistribution:
    """Grade distribution analysis."""

    overall: dict[str, int]
    by_class: dict[str, dict[str, int]]


@dataclass
class StudentPerformance:
    """Performance analysis for a single student."""

    student_id: str
    subject_averages: dict[str, float]
    overall_average: float
    strongest_subject: str
    weakest_subject: str
    trends: dict[str, int]


@dataclass
class ClassPerformance:
    """Performance analysis for a class."""

    class_name: str
    class_average: float
    student_averages: list[dict]
    quarterly_averages: list[dict]
    top_performer_id: str
    top_performer_avg: float


def calculate_subject_stats(df: pl.DataFrame, subjects: list[str]) -> dict[str, SubjectStats]:
    """Calculate statistics (mean, min, max, std) for each subject."""
    stats = {}
    for subject in subjects:
        col = df[subject]
        stats[subject] = SubjectStats(
            mean=round(col.mean(), 2),
            min=int(col.min()),
            max=int(col.max()),
            std=round(col.std(), 2) if len(df) > 1 else 0.0,
        )
    return stats


def calculate_overall_mean(df: pl.DataFrame, subjects: list[str]) -> float:
    """Calculate the overall mean across all subjects."""
    return round(df.select(subjects).mean().to_numpy().mean(), 2)


def analyze_scores(
    scores: list[dict],
    subjects: list[str],
) -> ScoreAnalysis:
    """Perform comprehensive analysis on score data."""
    df = pl.DataFrame(scores)

    subject_stats = calculate_subject_stats(df, subjects)
    overall_mean = calculate_overall_mean(df, subjects)

    return ScoreAnalysis(
        subject_stats=subject_stats,
        overall_mean=overall_mean,
        record_count=len(scores),
        unique_students=df["student_id"].n_unique(),
        unique_quarters=df["quarter"].n_unique() if "quarter" in df.columns else 1,
    )


def calculate_grade_distribution(
    grades: list[dict],
    classes: list[str],
) -> GradeDistribution:
    """Calculate grade distribution overall and by class."""
    overall = {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0}
    by_class = {cls: {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0} for cls in classes}

    for record in grades:
        for cls, grade in record["grades"].items():
            if cls in classes:
                overall[grade] += 1
                by_class[cls][grade] += 1

    return GradeDistribution(overall=overall, by_class=by_class)


def analyze_student_scores(
    scores: list[dict],
    subjects: list[str],
) -> StudentPerformance:
    """Analyze a single student's performance across quarters."""
    if not scores:
        raise ValueError("No scores provided")

    df = pl.DataFrame(scores)
    student_id = scores[0]["student_id"]

    # Calculate subject averages
    subject_averages = {}
    for subject in subjects:
        subject_averages[subject] = round(df[subject].mean(), 2)

    overall_avg = round(sum(subject_averages.values()) / len(subjects), 2)
    strongest = max(subject_averages, key=subject_averages.get)
    weakest = min(subject_averages, key=subject_averages.get)

    # Calculate trends (first quarter to last quarter)
    scores_sorted = sorted(scores, key=lambda x: x.get("quarter", 0))
    trends = {}
    for subject in subjects:
        first_q = scores_sorted[0].get(subject, 0)
        last_q = scores_sorted[-1].get(subject, 0)
        trends[subject] = last_q - first_q

    return StudentPerformance(
        student_id=student_id,
        subject_averages=subject_averages,
        overall_average=overall_avg,
        strongest_subject=strongest,
        weakest_subject=weakest,
        trends=trends,
    )


def analyze_class_scores(
    scores: list[dict],
    class_name: str,
) -> ClassPerformance:
    """Analyze class-wide performance across all students and quarters."""
    df = pl.DataFrame(scores)

    # Overall class average
    class_avg = round(df["score"].mean(), 2)

    # Student averages
    student_avgs = df.group_by("student_id").agg(pl.col("score").mean().alias("avg_score"))
    top_performer = student_avgs.sort("avg_score", descending=True).row(0)

    # Quarterly averages
    quarterly_avgs = df.group_by("quarter").agg(pl.col("score").mean().alias("avg_score")).sort("quarter")

    return ClassPerformance(
        class_name=class_name,
        class_average=class_avg,
        student_averages=student_avgs.to_dicts(),
        quarterly_averages=quarterly_avgs.to_dicts(),
        top_performer_id=top_performer[0],
        top_performer_avg=round(top_performer[1], 2),
    )


def compare_two_students(
    student1_scores: list[dict],
    student2_scores: list[dict],
    subjects: list[str],
) -> dict:
    """Compare two students across all subjects."""
    df1 = pl.DataFrame(student1_scores)
    df2 = pl.DataFrame(student2_scores)

    comparison = {}
    for subject in subjects:
        avg1 = round(df1[subject].mean(), 2)
        avg2 = round(df2[subject].mean(), 2)
        comparison[subject] = {
            "student1": avg1,
            "student2": avg2,
            "difference": round(avg1 - avg2, 2),
            "winner": "student1" if avg1 > avg2 else "student2" if avg2 > avg1 else "tie",
        }

    overall1 = round(sum(comparison[s]["student1"] for s in subjects) / len(subjects), 2)
    overall2 = round(sum(comparison[s]["student2"] for s in subjects) / len(subjects), 2)

    return {
        "comparison": comparison,
        "overall_averages": {"student1": overall1, "student2": overall2},
    }


def calculate_curriculum_completion(curriculum_data: list[dict]) -> dict[str, float]:
    """Calculate average completion rate per class."""
    class_rates: dict[str, list[float]] = {}
    for record in curriculum_data:
        cls = record["class"]
        rate = record["completion_rate"]
        if cls not in class_rates:
            class_rates[cls] = []
        class_rates[cls].append(rate)

    return {cls: round(sum(rates) / len(rates), 1) for cls, rates in class_rates.items()}
