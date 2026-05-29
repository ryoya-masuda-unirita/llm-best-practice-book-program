"""
Tool functions for data analysis following the ID reference pattern.

These tools are designed as composite functions that perform multiple operations
internally and return summaries with result IDs for the LLM context.
Each tool function composes smaller, testable functions from the functions module.

Output format is compatible with Pydantic output schemas for Tool Chain support.
"""

from src.logger import make_logger
from src.model import (
    ClassAnalysisResult,
    CurriculumResult,
    DataListResult,
    DetailedDataResult,
    GradeReportResult,
    ResultStorage,
    StudentAnalysisResult,
    StudentListResult,
    TestScoreResult,
)
from src.service.tools.functions import (
    VALID_CLASSES,
    analyze_class_scores,
    analyze_scores,
    analyze_student_scores,
    calculate_curriculum_completion,
    calculate_grade_distribution,
    compare_two_students,
    format_comparison_summary,
    format_filter_context,
    format_grade_distribution,
    generate_result_id,
    list_json_files,
    load_all_quarterly_curriculum,
    load_all_quarterly_grades,
    load_all_quarterly_scores,
    load_curriculum,
    load_grade_report,
    load_students,
    load_test_scores,
    truncate_id,
    validate_class_name,
    validate_classes,
    validate_quarter,
    validate_quarters,
    validate_result_id,
)

logger = make_logger(__name__)

result_storage = ResultStorage()


def _categorize_files(file_names: list[str]) -> set[str]:
    """Categorize file names by data type."""
    categories = set()
    for name in file_names:
        if "test_score" in name:
            categories.add("test_scores")
        elif "grade_report" in name:
            categories.add("grade_reports")
        elif "curriculum" in name:
            categories.add("curriculum")
        elif "students" in name:
            categories.add("students")
    return categories


def list_available_data() -> dict:
    """List all available data files, categorized by type, with result_id for details."""
    logger.info("Listing available data files")

    file_names = list_json_files()
    categories = _categorize_files(file_names)

    result_id = generate_result_id("list_data")
    result = DataListResult(
        tool_name="list_available_data",
        result_id=result_id,
        result_summary=f"Found {len(file_names)} data files in categories: {', '.join(sorted(categories))}",
        file_count=len(file_names),
        file_categories=sorted(categories),
    )

    result_storage.store(result_id, {"files": file_names, "categories": list(categories)}, result)

    return {
        "tool_name": "list_available_data",
        "result_id": result_id,
        "result_summary": result.result_summary,
        "success": True,
        "file_count": len(file_names),
        "file_categories": sorted(categories),
        "files": file_names,
    }


def get_students() -> dict:
    """Get the list of all students with count and IDs."""
    logger.info("Getting student list")

    students = load_students()
    student_ids = [s["id"] for s in students]

    result_id = generate_result_id("students")
    result = StudentListResult(
        tool_name="get_students",
        result_id=result_id,
        result_summary=f"Found {len(students)} students in the system",
        student_count=len(students),
        student_ids=student_ids,
    )

    result_storage.store(result_id, students, result)

    return {
        "tool_name": "get_students",
        "result_id": result_id,
        "result_summary": result.result_summary,
        "success": True,
        "student_count": len(students),
        "student_ids": student_ids,
    }


def get_test_scores(quarter: int) -> dict:
    """Get test scores for a specific quarter with statistical analysis."""
    logger.info(f"Getting test scores for quarter {quarter}")

    validation = validate_quarter(quarter)
    if not validation.is_valid:
        return {
            "tool_name": "get_test_scores",
            "result_id": "",
            "result_summary": f"Error: {validation.error_message}",
            "success": False,
            "error_message": validation.error_message,
            "quarter": quarter,
            "student_count": 0,
            "subjects": [],
            "subject_stats": {},
            "overall_average": 0.0,
            "scores": [],
        }

    scores = load_test_scores(quarter)
    subjects = VALID_CLASSES
    analysis = analyze_scores(scores, subjects)

    result_id = generate_result_id("test_scores", f"q{quarter}")
    result = TestScoreResult(
        tool_name="get_test_scores",
        result_id=result_id,
        result_summary=f"Quarter {quarter} test scores: {analysis.record_count} students, {len(subjects)} subjects. Overall average: {analysis.overall_mean}",
        quarter=quarter,
        student_count=analysis.record_count,
        subjects=subjects,
    )

    stats = {
        subj: {"mean": s.mean, "min": s.min, "max": s.max, "std": s.std} for subj, s in analysis.subject_stats.items()
    }

    result_storage.store(
        result_id,
        {"scores": scores, "statistics": stats},
        result,
    )

    return {
        "tool_name": "get_test_scores",
        "result_id": result_id,
        "result_summary": result.result_summary,
        "success": True,
        "quarter": quarter,
        "student_count": analysis.record_count,
        "subjects": subjects,
        "subject_stats": stats,
        "overall_average": analysis.overall_mean,
        "scores": scores,
    }


def get_grade_report(quarter: int) -> dict:
    """Get grade reports for a specific quarter with grade distribution."""
    logger.info(f"Getting grade report for quarter {quarter}")

    validation = validate_quarter(quarter)
    if not validation.is_valid:
        return {
            "tool_name": "get_grade_report",
            "result_id": "",
            "result_summary": f"Error: {validation.error_message}",
            "success": False,
            "error_message": validation.error_message,
            "quarter": quarter,
            "student_count": 0,
            "grade_distribution": {},
            "reports": [],
        }

    reports = load_grade_report(quarter)
    distribution = calculate_grade_distribution(reports, VALID_CLASSES)

    result_id = generate_result_id("grade_report", f"q{quarter}")
    dist_str = format_grade_distribution(distribution.overall)

    result = GradeReportResult(
        tool_name="get_grade_report",
        result_id=result_id,
        result_summary=f"Quarter {quarter} grades: {len(reports)} students. Distribution - {dist_str}",
        quarter=quarter,
        student_count=len(reports),
    )

    result_storage.store(
        result_id,
        {"reports": reports, "grade_distribution": distribution.overall},
        result,
    )

    return {
        "tool_name": "get_grade_report",
        "result_id": result_id,
        "result_summary": result.result_summary,
        "success": True,
        "quarter": quarter,
        "student_count": len(reports),
        "grade_distribution": distribution.overall,
        "reports": reports,
    }


def get_curriculum(quarter: int) -> dict:
    """Get curriculum information for a specific quarter with completion rates."""
    logger.info(f"Getting curriculum for quarter {quarter}")

    validation = validate_quarter(quarter)
    if not validation.is_valid:
        return {
            "tool_name": "get_curriculum",
            "result_id": "",
            "result_summary": f"Error: {validation.error_message}",
            "success": False,
            "error_message": validation.error_message,
            "quarter": quarter,
            "subjects": [],
            "average_completion": 0.0,
            "curriculum_data": {},
        }

    curriculum = load_curriculum(quarter)
    subjects = list(curriculum["classes"].keys())
    avg_completion = round(
        sum(curriculum["classes"][s]["completion_rate"] for s in subjects) / len(subjects),
        1,
    )

    result_id = generate_result_id("curriculum", f"q{quarter}")
    result = CurriculumResult(
        tool_name="get_curriculum",
        result_id=result_id,
        result_summary=f"Quarter {quarter} curriculum: {len(subjects)} subjects with average completion rate of {avg_completion}%",
        quarter=quarter,
        subjects=subjects,
    )

    result_storage.store(result_id, curriculum, result)

    return {
        "tool_name": "get_curriculum",
        "result_id": result_id,
        "result_summary": result.result_summary,
        "success": True,
        "quarter": quarter,
        "subjects": subjects,
        "average_completion": avg_completion,
        "curriculum_data": curriculum,
    }


def _collect_student_data(student_id: str) -> tuple[list[dict], list[dict], list[dict]]:
    """Collect all quarterly data for a student."""
    all_scores = []
    all_grades = []
    all_advice = []

    all_quarterly_scores = load_all_quarterly_scores()
    all_quarterly_grades = load_all_quarterly_grades()

    for quarter in range(1, 5):
        scores = all_quarterly_scores[quarter]
        grades = all_quarterly_grades[quarter]

        student_score = next((s for s in scores if s["student_id"] == student_id), None)
        student_grade = next((g for g in grades if g["student_id"] == student_id), None)

        if student_score:
            student_score["quarter"] = quarter
            all_scores.append(student_score)

        if student_grade:
            all_grades.append({"quarter": quarter, "grades": student_grade["grades"]})
            all_advice.append({"quarter": quarter, "advice": student_grade["teacher_advice"]})

    return all_scores, all_grades, all_advice


def analyze_student_performance(student_id: str) -> dict:
    """Comprehensive analysis of a student's performance across all quarters."""
    logger.info(f"Analyzing student performance for {student_id}")

    all_scores, all_grades, all_advice = _collect_student_data(student_id)

    if not all_scores:
        return {
            "tool_name": "analyze_student_performance",
            "result_id": "",
            "result_summary": f"Error: Student {student_id} not found in records.",
            "success": False,
            "error_message": f"Student {student_id} not found in records.",
            "student_id": student_id,
            "quarters_analyzed": [],
            "overall_average": 0.0,
            "subject_averages": {},
            "strongest_subject": "",
            "weakest_subject": "",
            "trends": {},
            "quarterly_scores": [],
            "quarterly_grades": [],
            "teacher_advice": [],
        }

    subjects = VALID_CLASSES
    performance = analyze_student_scores(all_scores, subjects)

    result_id = generate_result_id("student_analysis", truncate_id(student_id))
    result = StudentAnalysisResult(
        tool_name="analyze_student_performance",
        result_id=result_id,
        result_summary=f"Student {truncate_id(student_id)}... analysis complete. Overall average: {performance.overall_average}. Strongest: {performance.strongest_subject} ({performance.subject_averages[performance.strongest_subject]}). Weakest: {performance.weakest_subject} ({performance.subject_averages[performance.weakest_subject]}).",
        student_id=student_id,
        quarters_analyzed=[1, 2, 3, 4],
        overall_average=performance.overall_average,
        strongest_subject=performance.strongest_subject,
        weakest_subject=performance.weakest_subject,
    )

    detailed_data = {
        "student_id": student_id,
        "quarterly_scores": all_scores,
        "quarterly_grades": all_grades,
        "teacher_advice": all_advice,
        "subject_averages": performance.subject_averages,
        "trends": performance.trends,
        "overall_average": performance.overall_average,
    }

    result_storage.store(result_id, detailed_data, result)

    return {
        "tool_name": "analyze_student_performance",
        "result_id": result_id,
        "result_summary": result.result_summary,
        "success": True,
        "student_id": student_id,
        "quarters_analyzed": [1, 2, 3, 4],
        "overall_average": performance.overall_average,
        "subject_averages": performance.subject_averages,
        "strongest_subject": performance.strongest_subject,
        "weakest_subject": performance.weakest_subject,
        "trends": performance.trends,
        "quarterly_scores": all_scores,
        "quarterly_grades": all_grades,
        "teacher_advice": all_advice,
    }


def _collect_class_data(class_name: str) -> tuple[list[dict], list[dict]]:
    """Collect all quarterly data for a class."""
    all_scores = []
    curriculum_completion = []

    all_quarterly_scores = load_all_quarterly_scores()
    all_quarterly_curriculum = load_all_quarterly_curriculum()

    for quarter in range(1, 5):
        scores = all_quarterly_scores[quarter]
        curriculum = all_quarterly_curriculum[quarter]

        for score in scores:
            all_scores.append(
                {
                    "student_id": score["student_id"],
                    "quarter": quarter,
                    "score": score[class_name],
                }
            )

        curriculum_completion.append(
            {
                "quarter": quarter,
                "completion_rate": curriculum["classes"][class_name]["completion_rate"],
            }
        )

    return all_scores, curriculum_completion


def analyze_class_performance(class_name: str) -> dict:
    """Comprehensive analysis of a class's performance across all students and quarters."""
    logger.info(f"Analyzing class performance for {class_name}")

    validation = validate_class_name(class_name)
    if not validation.is_valid:
        return {
            "tool_name": "analyze_class_performance",
            "result_id": "",
            "result_summary": f"Error: {validation.error_message}",
            "success": False,
            "error_message": validation.error_message,
            "class_name": class_name,
            "quarters_analyzed": [],
            "class_average": 0.0,
            "top_performer_id": "",
            "top_performer_avg": 0.0,
            "curriculum_completion_avg": 0.0,
            "student_averages": [],
            "quarterly_averages": [],
        }

    class_name = validation.value

    all_scores, curriculum_completion = _collect_class_data(class_name)
    class_analysis = analyze_class_scores(all_scores, class_name)

    avg_curriculum = round(
        sum(c["completion_rate"] for c in curriculum_completion) / len(curriculum_completion),
        1,
    )

    result_id = generate_result_id("class_analysis", class_name)
    result = ClassAnalysisResult(
        tool_name="analyze_class_performance",
        result_id=result_id,
        result_summary=f"{class_name.capitalize()} class analysis: Average score {class_analysis.class_average}, Top performer: {truncate_id(class_analysis.top_performer_id)}... ({class_analysis.top_performer_avg}). Curriculum completion: {avg_curriculum}%",
        class_name=class_name,
        quarters_analyzed=[1, 2, 3, 4],
        class_average=class_analysis.class_average,
        top_performer_id=class_analysis.top_performer_id,
        curriculum_completion_avg=avg_curriculum,
    )

    detailed_data = {
        "class_name": class_name,
        "all_scores": all_scores,
        "student_averages": class_analysis.student_averages,
        "quarterly_averages": class_analysis.quarterly_averages,
        "curriculum_completion": curriculum_completion,
        "class_average": class_analysis.class_average,
        "top_performer": {
            "id": class_analysis.top_performer_id,
            "average": class_analysis.top_performer_avg,
        },
    }

    result_storage.store(result_id, detailed_data, result)

    return {
        "tool_name": "analyze_class_performance",
        "result_id": result_id,
        "result_summary": result.result_summary,
        "success": True,
        "class_name": class_name,
        "quarters_analyzed": [1, 2, 3, 4],
        "class_average": class_analysis.class_average,
        "top_performer_id": class_analysis.top_performer_id,
        "top_performer_avg": class_analysis.top_performer_avg,
        "curriculum_completion_avg": avg_curriculum,
        "student_averages": class_analysis.student_averages,
        "quarterly_averages": class_analysis.quarterly_averages,
    }


def get_result_details(result_id: str) -> dict:
    """Retrieve detailed data for a previously computed result (pull pattern)."""
    logger.info(f"Retrieving details for result {result_id}")

    validation = validate_result_id(result_id, result_storage.list_ids())
    if not validation.is_valid:
        return {
            "tool_name": "get_result_details",
            "result_id": "",
            "result_summary": f"Error: {validation.error_message}",
            "success": False,
            "error_message": validation.error_message,
            "original_result_id": result_id,
            "data_type": "unknown",
            "detailed_data": None,
        }

    stored = result_storage.get(result_id)
    data, metadata = stored

    new_result_id = generate_result_id("details", result_id[:20])
    result = DetailedDataResult(
        tool_name="get_result_details",
        result_id=new_result_id,
        result_summary=f"Retrieved detailed data for {result_id}. Data type: {type(data).__name__}",
        original_result_id=result_id,
        data_type=metadata.tool_name if metadata else "unknown",
    )

    return {
        "tool_name": "get_result_details",
        "result_id": new_result_id,
        "result_summary": result.result_summary,
        "success": True,
        "original_result_id": result_id,
        "data_type": metadata.tool_name if metadata else "unknown",
        "detailed_data": data,
    }


def _collect_comparison_data(
    student_id_1: str,
    student_id_2: str,
) -> tuple[list[dict], list[dict]]:
    """Collect quarterly score data for two students."""
    student1_data = []
    student2_data = []

    all_quarterly_scores = load_all_quarterly_scores()

    for quarter in range(1, 5):
        scores = all_quarterly_scores[quarter]

        s1 = next((s for s in scores if s["student_id"] == student_id_1), None)
        s2 = next((s for s in scores if s["student_id"] == student_id_2), None)

        if s1:
            s1["quarter"] = quarter
            student1_data.append(s1)
        if s2:
            s2["quarter"] = quarter
            student2_data.append(s2)

    return student1_data, student2_data


def compare_students(student_id_1: str, student_id_2: str) -> dict:
    """Compare performance between two students across all quarters."""
    logger.info(f"Comparing students {truncate_id(student_id_1)}... and {truncate_id(student_id_2)}...")

    student1_data, student2_data = _collect_comparison_data(student_id_1, student_id_2)

    if not student1_data or not student2_data:
        missing = []
        if not student1_data:
            missing.append(truncate_id(student_id_1))
        if not student2_data:
            missing.append(truncate_id(student_id_2))
        return {
            "tool_name": "compare_students",
            "result_id": "",
            "result_summary": f"Error: Student(s) not found: {', '.join(missing)}...",
            "success": False,
            "error_message": f"Student(s) not found: {', '.join(missing)}...",
            "student1_id": student_id_1,
            "student2_id": student_id_2,
            "comparison": {},
            "overall_averages": {},
            "student1_scores": [],
            "student2_scores": [],
        }

    subjects = VALID_CLASSES
    comparison_result = compare_two_students(student1_data, student2_data, subjects)

    result_id = generate_result_id("compare", f"{student_id_1[:4]}_{student_id_2[:4]}")

    summary_parts = format_comparison_summary(comparison_result["comparison"], subjects)
    overall = comparison_result["overall_averages"]

    detailed_data = {
        "student1_id": student_id_1,
        "student2_id": student_id_2,
        "student1_scores": student1_data,
        "student2_scores": student2_data,
        "comparison": comparison_result["comparison"],
        "overall_averages": overall,
    }

    result_storage.store(result_id, detailed_data, None)

    return {
        "tool_name": "compare_students",
        "result_id": result_id,
        "result_summary": f"Comparison complete. Overall: S1={overall['student1']}, S2={overall['student2']}. {summary_parts}",
        "success": True,
        "student1_id": student_id_1,
        "student2_id": student_id_2,
        "comparison": comparison_result["comparison"],
        "overall_averages": overall,
        "student1_scores": student1_data,
        "student2_scores": student2_data,
    }


def _collect_filtered_scores(
    classes: list[str],
    student_ids: list[str] | None,
    quarters: list[int],
) -> list[dict]:
    """Collect and filter score data."""
    all_scores = []

    for quarter in quarters:
        scores = load_test_scores(quarter)

        for score in scores:
            if student_ids and score["student_id"] not in student_ids:
                continue

            filtered_score = {
                "student_id": score["student_id"],
                "quarter": quarter,
            }
            for cls in classes:
                filtered_score[cls] = score[cls]

            all_scores.append(filtered_score)

    return all_scores


def filter_scores(
    classes: list[str] | None = None,
    student_ids: list[str] | None = None,
    quarters: list[int] | None = None,
) -> dict:
    """Filter and retrieve test scores by classes, students, and/or quarters."""
    logger.info(f"Filtering scores - classes: {classes}, students: {student_ids}, quarters: {quarters}")

    class_validation = validate_classes(classes)
    if not class_validation.is_valid:
        return {
            "tool_name": "filter_scores",
            "result_id": "",
            "result_summary": f"Error: {class_validation.error_message}",
            "success": False,
            "error_message": class_validation.error_message,
            "record_count": 0,
            "unique_students": 0,
            "unique_quarters": 0,
            "overall_average": 0.0,
            "filters_applied": {},
            "subject_stats": {},
            "scores": [],
        }
    classes = class_validation.value

    quarter_validation = validate_quarters(quarters)
    if not quarter_validation.is_valid:
        return {
            "tool_name": "filter_scores",
            "result_id": "",
            "result_summary": f"Error: {quarter_validation.error_message}",
            "success": False,
            "error_message": quarter_validation.error_message,
            "record_count": 0,
            "unique_students": 0,
            "unique_quarters": 0,
            "overall_average": 0.0,
            "filters_applied": {},
            "subject_stats": {},
            "scores": [],
        }
    quarters = quarter_validation.value

    all_scores = _collect_filtered_scores(classes, student_ids, quarters)

    if not all_scores:
        return {
            "tool_name": "filter_scores",
            "result_id": "",
            "result_summary": "Error: No data found matching the specified filters.",
            "success": False,
            "error_message": "No data found matching the specified filters.",
            "record_count": 0,
            "unique_students": 0,
            "unique_quarters": 0,
            "overall_average": 0.0,
            "filters_applied": {"classes": classes, "student_ids": student_ids, "quarters": quarters},
            "subject_stats": {},
            "scores": [],
        }

    analysis = analyze_scores(all_scores, classes)

    stats = {
        subj: {"mean": s.mean, "min": s.min, "max": s.max, "std": s.std} for subj, s in analysis.subject_stats.items()
    }

    context = format_filter_context(classes, student_ids, quarters)
    result_id = generate_result_id("filter_scores", context)

    detailed_data = {
        "filters": {
            "classes": classes,
            "student_ids": student_ids,
            "quarters": quarters,
        },
        "scores": all_scores,
        "statistics": stats,
        "overall_average": analysis.overall_mean,
        "record_count": analysis.record_count,
        "unique_students": analysis.unique_students,
        "unique_quarters": analysis.unique_quarters,
    }

    result_storage.store(result_id, detailed_data, None)

    return {
        "tool_name": "filter_scores",
        "result_id": result_id,
        "result_summary": f"Filtered data: {analysis.record_count} records, {analysis.unique_students} students, {analysis.unique_quarters} quarters, {len(classes)} classes. Overall avg: {analysis.overall_mean}",
        "success": True,
        "record_count": analysis.record_count,
        "unique_students": analysis.unique_students,
        "unique_quarters": analysis.unique_quarters,
        "overall_average": analysis.overall_mean,
        "filters_applied": {"classes": classes, "student_ids": student_ids, "quarters": quarters},
        "subject_stats": stats,
        "scores": all_scores,
    }


def _collect_filtered_grades(
    classes: list[str],
    student_ids: list[str] | None,
    quarters: list[int],
) -> tuple[list[dict], list[dict]]:
    """Collect and filter grade data."""
    all_grades = []
    all_advice = []

    for quarter in quarters:
        reports = load_grade_report(quarter)

        for report in reports:
            if student_ids and report["student_id"] not in student_ids:
                continue

            filtered_grades = {}
            for cls in classes:
                filtered_grades[cls] = report["grades"][cls]

            all_grades.append(
                {
                    "student_id": report["student_id"],
                    "quarter": quarter,
                    "grades": filtered_grades,
                }
            )

            all_advice.append(
                {
                    "student_id": report["student_id"],
                    "quarter": quarter,
                    "teacher_advice": report["teacher_advice"],
                }
            )

    return all_grades, all_advice


def filter_grades(
    classes: list[str] | None = None,
    student_ids: list[str] | None = None,
    quarters: list[int] | None = None,
) -> dict:
    """Filter and retrieve grade reports by classes, students, and/or quarters."""
    logger.info(f"Filtering grades - classes: {classes}, students: {student_ids}, quarters: {quarters}")

    class_validation = validate_classes(classes)
    if not class_validation.is_valid:
        return {
            "tool_name": "filter_grades",
            "result_id": "",
            "result_summary": f"Error: {class_validation.error_message}",
            "success": False,
            "error_message": class_validation.error_message,
            "record_count": 0,
            "unique_students": 0,
            "unique_quarters": 0,
            "filters_applied": {},
            "overall_distribution": {},
            "class_distribution": {},
            "grades": [],
            "teacher_advice": [],
        }
    classes = class_validation.value

    quarter_validation = validate_quarters(quarters)
    if not quarter_validation.is_valid:
        return {
            "tool_name": "filter_grades",
            "result_id": "",
            "result_summary": f"Error: {quarter_validation.error_message}",
            "success": False,
            "error_message": quarter_validation.error_message,
            "record_count": 0,
            "unique_students": 0,
            "unique_quarters": 0,
            "filters_applied": {},
            "overall_distribution": {},
            "class_distribution": {},
            "grades": [],
            "teacher_advice": [],
        }
    quarters = quarter_validation.value

    all_grades, all_advice = _collect_filtered_grades(classes, student_ids, quarters)

    if not all_grades:
        return {
            "tool_name": "filter_grades",
            "result_id": "",
            "result_summary": "Error: No data found matching the specified filters.",
            "success": False,
            "error_message": "No data found matching the specified filters.",
            "record_count": 0,
            "unique_students": 0,
            "unique_quarters": 0,
            "filters_applied": {"classes": classes, "student_ids": student_ids, "quarters": quarters},
            "overall_distribution": {},
            "class_distribution": {},
            "grades": [],
            "teacher_advice": [],
        }

    distribution = calculate_grade_distribution(all_grades, classes)

    unique_students = len(set(g["student_id"] for g in all_grades))
    unique_quarters = len(set(g["quarter"] for g in all_grades))

    context = format_filter_context(classes, student_ids, quarters)
    result_id = generate_result_id("filter_grades", context)

    dist_str = format_grade_distribution(distribution.overall)

    detailed_data = {
        "filters": {
            "classes": classes,
            "student_ids": student_ids,
            "quarters": quarters,
        },
        "grades": all_grades,
        "teacher_advice": all_advice,
        "overall_distribution": distribution.overall,
        "class_distribution": distribution.by_class,
        "record_count": len(all_grades),
        "unique_students": unique_students,
        "unique_quarters": unique_quarters,
    }

    result_storage.store(result_id, detailed_data, None)

    return {
        "tool_name": "filter_grades",
        "result_id": result_id,
        "result_summary": f"Filtered grades: {len(all_grades)} records, {unique_students} students, {unique_quarters} quarters. Distribution: {dist_str}",
        "success": True,
        "record_count": len(all_grades),
        "unique_students": unique_students,
        "unique_quarters": unique_quarters,
        "filters_applied": {"classes": classes, "student_ids": student_ids, "quarters": quarters},
        "overall_distribution": distribution.overall,
        "class_distribution": distribution.by_class,
        "grades": all_grades,
        "teacher_advice": all_advice,
    }


def _collect_filtered_curriculum(
    classes: list[str],
    quarters: list[int],
) -> list[dict]:
    """Collect and filter curriculum data."""
    curriculum_data = []

    for quarter in quarters:
        curriculum = load_curriculum(quarter)

        for cls in classes:
            cls_data = curriculum["classes"][cls]
            curriculum_data.append(
                {
                    "quarter": quarter,
                    "class": cls,
                    "plan": cls_data["plan"],
                    "actual_progress": cls_data["actual_progress"],
                    "completion_rate": cls_data["completion_rate"],
                }
            )

    return curriculum_data


def filter_curriculum(
    classes: list[str] | None = None,
    quarters: list[int] | None = None,
) -> dict:
    """Filter and retrieve curriculum data by classes and/or quarters."""
    logger.info(f"Filtering curriculum - classes: {classes}, quarters: {quarters}")

    class_validation = validate_classes(classes)
    if not class_validation.is_valid:
        return {
            "tool_name": "filter_curriculum",
            "result_id": "",
            "result_summary": f"Error: {class_validation.error_message}",
            "success": False,
            "error_message": class_validation.error_message,
            "record_count": 0,
            "average_completion": 0.0,
            "filters_applied": {},
            "class_completion": {},
            "curriculum": [],
        }
    classes = class_validation.value

    quarter_validation = validate_quarters(quarters)
    if not quarter_validation.is_valid:
        return {
            "tool_name": "filter_curriculum",
            "result_id": "",
            "result_summary": f"Error: {quarter_validation.error_message}",
            "success": False,
            "error_message": quarter_validation.error_message,
            "record_count": 0,
            "average_completion": 0.0,
            "filters_applied": {},
            "class_completion": {},
            "curriculum": [],
        }
    quarters = quarter_validation.value

    curriculum_data = _collect_filtered_curriculum(classes, quarters)

    if not curriculum_data:
        return {
            "tool_name": "filter_curriculum",
            "result_id": "",
            "result_summary": "Error: No data found matching the specified filters.",
            "success": False,
            "error_message": "No data found matching the specified filters.",
            "record_count": 0,
            "average_completion": 0.0,
            "filters_applied": {"classes": classes, "quarters": quarters},
            "class_completion": {},
            "curriculum": [],
        }

    completion_rates = calculate_curriculum_completion(curriculum_data)
    avg_completion = round(
        sum(d["completion_rate"] for d in curriculum_data) / len(curriculum_data),
        1,
    )

    context = format_filter_context(classes, None, quarters)
    result_id = generate_result_id("filter_curriculum", context)

    detailed_data = {
        "filters": {
            "classes": classes,
            "quarters": quarters,
        },
        "curriculum": curriculum_data,
        "average_completion": avg_completion,
        "class_completion": completion_rates,
        "record_count": len(curriculum_data),
    }

    result_storage.store(result_id, detailed_data, None)

    return {
        "tool_name": "filter_curriculum",
        "result_id": result_id,
        "result_summary": f"Filtered curriculum: {len(curriculum_data)} records, {len(classes)} classes, {len(quarters)} quarters. Avg completion: {avg_completion}%",
        "success": True,
        "record_count": len(curriculum_data),
        "average_completion": avg_completion,
        "filters_applied": {"classes": classes, "quarters": quarters},
        "class_completion": completion_rates,
        "curriculum": curriculum_data,
    }
