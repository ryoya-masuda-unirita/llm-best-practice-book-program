"""
Prompt definitions for the data analysis LLM application.

This module defines the system prompt and tool declarations for Anthropic function calling.
"""

from anthropic.types import ToolParam

SYSTEM_PROMPT = """You are an intelligent data analysis assistant for a school management system.
You have access to student records, test scores, grade reports, and curriculum data.

## CRITICAL: Language Requirement
You MUST respond in the SAME LANGUAGE as the user's request:
- ユーザーが日本語で質問した場合は、必ず日本語でレポートを作成してください。
- If the user writes in English, respond entirely in English.
- This applies to ALL sections of your report including headings.

## Available Data
- Student records with unique UUIDs
- Quarterly test scores (4 quarters) for 5 subjects: Japanese, Math, Physics, History, PE
- Grade reports with letter grades (A, B, C, D, F) and teacher advice
- Curriculum plans and actual progress for each quarter

## Your Capabilities
You can analyze this data using the provided tools to:
1. List available data files
2. Retrieve student information
3. Get test scores and grade reports by quarter
4. Get curriculum information
5. Perform comprehensive student performance analysis
6. Analyze class-wide performance
7. Compare two students
8. Retrieve detailed data using result IDs

## Important Guidelines
- Tool calls return summaries with result IDs. Use get_result_details to retrieve full data when needed.
- The result_id in each response can be used to fetch detailed information later.
- When analyzing data, explain your findings clearly and provide actionable insights.
- Always cite which data you used (by result_id) when making conclusions.
- If you need more detailed information, use get_result_details with the appropriate result_id.

## CRITICAL: Final Report Requirement
You MUST ALWAYS produce a comprehensive, well-structured analysis report as your final output.
After gathering all necessary data through tool calls, you MUST write a complete report.
Never end with just tool call results - always synthesize the data into a final report.

### Report Structure (use headings in the user's language)

For Japanese requests, use these headings:
1. **概要** - 分析の概要と主要な発見事項
2. **データ分析** - 詳細な分析結果（具体的な数値とパーセンテージを含む）
3. **強み** - 良好な点、優れている領域
4. **改善点** - 課題、問題点、目標との乖離
5. **提案** - 具体的で実行可能な改善提案（優先順位付き）
6. **データソース** - 使用したresult_idの一覧

For English requests, use these headings:
1. **Executive Summary** - Overview and key findings
2. **Data Analysis** - Detailed findings with specific numbers and percentages
3. **Strengths** - Positive aspects and areas of excellence
4. **Areas for Improvement** - Issues, concerns, and gaps
5. **Recommendations** - Actionable suggestions with priorities
6. **Data Sources** - List of result_ids used

### Report Guidelines
- Use clear headings with markdown formatting
- Include specific numbers, percentages, and statistics
- Provide bullet points for easy reading
- Make recommendations concrete and actionable
- Always cite data sources with result_ids
"""

# Tool declarations for Anthropic function calling
TOOL_DECLARATIONS = [
    {
        "name": "list_available_data",
        "description": "List all available data files in the data directory. Returns a summary of available data categories including test scores, grade reports, curriculum, and student records.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_students",
        "description": "Get the list of all students in the system. Returns student count and their UUIDs.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_test_scores",
        "description": "Get test scores for a specific quarter. Returns statistics including averages for each subject.",
        "parameters": {
            "type": "object",
            "properties": {
                "quarter": {
                    "type": "integer",
                    "description": "Quarter number. Must be 1, 2, 3, or 4.",
                },
            },
            "required": ["quarter"],
        },
    },
    {
        "name": "get_grade_report",
        "description": "Get grade reports for a specific quarter. Returns grade distribution (A, B, C, D, F) and includes teacher advice for each student.",
        "parameters": {
            "type": "object",
            "properties": {
                "quarter": {
                    "type": "integer",
                    "description": "Quarter number. Must be 1, 2, 3, or 4.",
                },
            },
            "required": ["quarter"],
        },
    },
    {
        "name": "get_curriculum",
        "description": "Get curriculum information for a specific quarter. Returns planned topics, actual progress, and completion rates for each subject.",
        "parameters": {
            "type": "object",
            "properties": {
                "quarter": {
                    "type": "integer",
                    "description": "Quarter number. Must be 1, 2, 3, or 4.",
                },
            },
            "required": ["quarter"],
        },
    },
    {
        "name": "analyze_student_performance",
        "description": "Comprehensive analysis of a student's performance across all quarters. This composite function loads all quarterly test scores, calculates trends, identifies strengths and weaknesses, and compiles grade history with teacher feedback.",
        "parameters": {
            "type": "object",
            "properties": {
                "student_id": {
                    "type": "string",
                    "description": "The UUID of the student to analyze",
                },
            },
            "required": ["student_id"],
        },
    },
    {
        "name": "analyze_class_performance",
        "description": "Comprehensive analysis of a class's performance across all students and quarters. Identifies top performers, calculates class averages, and correlates with curriculum completion rates.",
        "parameters": {
            "type": "object",
            "properties": {
                "class_name": {
                    "type": "string",
                    "description": "Name of the class to analyze",
                    "enum": ["japanese", "math", "physics", "history", "pe"],
                },
            },
            "required": ["class_name"],
        },
    },
    {
        "name": "get_result_details",
        "description": "Retrieve detailed data for a previously computed result using its result_id. Use this to get full data when the summary is not sufficient for analysis.",
        "parameters": {
            "type": "object",
            "properties": {
                "result_id": {
                    "type": "string",
                    "description": "The result ID from a previous tool call",
                },
            },
            "required": ["result_id"],
        },
    },
    {
        "name": "compare_students",
        "description": "Compare performance between two students across all quarters. Provides subject-by-subject comparison and identifies which student performs better in each area.",
        "parameters": {
            "type": "object",
            "properties": {
                "student_id_1": {
                    "type": "string",
                    "description": "UUID of the first student",
                },
                "student_id_2": {
                    "type": "string",
                    "description": "UUID of the second student",
                },
            },
            "required": ["student_id_1", "student_id_2"],
        },
    },
    {
        "name": "filter_scores",
        "description": "Filter and retrieve test scores with flexible filtering. Supports filtering by multiple classes (e.g., only math and physics for STEM analysis), multiple students, and multiple quarters. All filters are optional and combined with AND logic. Returns filtered data with statistics.",
        "parameters": {
            "type": "object",
            "properties": {
                "classes": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of class names to include: japanese, math, physics, history, pe. Example: ['math', 'physics'] for STEM subjects. If not specified, all classes are included.",
                },
                "student_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of student UUIDs to include. If not specified, all students are included.",
                },
                "quarters": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "List of quarter numbers (1-4) to include. Example: [1, 2] for first half of year. If not specified, all quarters are included.",
                },
            },
            "required": [],
        },
    },
    {
        "name": "filter_grades",
        "description": "Filter and retrieve grade reports with flexible filtering. Supports filtering by multiple classes, multiple students, and multiple quarters. Returns filtered grades with distribution statistics.",
        "parameters": {
            "type": "object",
            "properties": {
                "classes": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of class names to include: japanese, math, physics, history, pe. If not specified, all classes are included.",
                },
                "student_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of student UUIDs to include. If not specified, all students are included.",
                },
                "quarters": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "List of quarter numbers (1-4) to include. If not specified, all quarters are included.",
                },
            },
            "required": [],
        },
    },
    {
        "name": "filter_curriculum",
        "description": "Filter and retrieve curriculum data with flexible filtering. Supports filtering by multiple classes and multiple quarters. Returns filtered curriculum with completion rates.",
        "parameters": {
            "type": "object",
            "properties": {
                "classes": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of class names to include: japanese, math, physics, history, pe. If not specified, all classes are included.",
                },
                "quarters": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "List of quarter numbers (1-4) to include. If not specified, all quarters are included.",
                },
            },
            "required": [],
        },
    },
]


def get_tools() -> list[ToolParam]:
    """Get the tool definitions for Anthropic tool use."""
    return [
        {
            "name": declaration["name"],
            "description": declaration["description"],
            "input_schema": declaration["parameters"],
        }
        for declaration in TOOL_DECLARATIONS
    ]


def get_system_prompt() -> str:
    """Get the system prompt for the data analysis assistant."""
    return SYSTEM_PROMPT
