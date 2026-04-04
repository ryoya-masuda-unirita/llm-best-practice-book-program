"""
Advanced Example: Complete Prompt Analysis and Continuous Improvement

This example demonstrates the full workflow including:
1. Logging multiple prompt executions (both successes and failures)
2. Creating templates from successful prompts
3. Identifying and recording anti-patterns from failures
4. Generating analytics and performance reports
5. Getting improvement suggestions
6. Cost analysis and optimization

Use Case: Multi-agent AI system for inventory optimization
Scenario: An AI agent generates prompts to analyze demand patterns and optimize stock levels
"""

import asyncio
import random
from datetime import datetime
from pathlib import Path
from typing import List

from src.client.llm_client import OpenAIModel
from src.model.prompt_log import (
    EvaluationCriteria,
    EvaluationStatus,
    PromptCategory,
    PromptMetadata,
)
from src.service.prompt_analytics import PromptAnalytics
from src.service.prompt_analyzer import PromptAnalyzer
from src.service.prompt_service import PromptManagementService
from src.service.prompt_storage import PromptStorage

PROJECT_ROOT = Path(__file__).parent.parent.parent
STORAGE_DIR = PROJECT_ROOT / "prompt_storage"

PRODUCTS = ["PROD-001", "PROD-002", "PROD-003", "PROD-004", "PROD-005"]
SEASONAL_TRENDS = ["increasing", "stable", "decreasing"]
MARKET_CONDITIONS = ["favorable", "neutral", "challenging"]


def print_section_header(title: str):
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80 + "\n")


def print_step_header(title: str = ""):
    if title:
        print(f"\n{title}")
    print("-" * 80)


class InventoryOptimizationAgent:
    def __init__(self, prompt_service: PromptManagementService):
        self.prompt_service = prompt_service
        self.session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    def generate_prompt_text(self, product_id: str, historical_data: dict) -> str:
        return f"""Analyze the demand pattern for product {product_id} based on:
        - Last 30 days sales: {historical_data.get("sales_30d", "N/A")}
        - Seasonal trend: {historical_data.get("seasonal_trend", "N/A")}
        - Market conditions: {historical_data.get("market_conditions", "N/A")}

        Provide:
        1. Predicted demand for next 7 days
        2. Recommended stock level
        3. Reorder threshold
        4. Confidence score (0-1)
        """

    def create_messages(self, prompt_text: str) -> list[dict]:
        return [
            {
                "role": "system",
                "content": "You are an expert inventory optimization AI. Provide data-driven recommendations.",
            },
            {"role": "user", "content": prompt_text},
        ]

    def simulate_execution(self, prompt_text: str) -> tuple[float, int, int, bool]:
        execution_time_ms = random.uniform(500, 2000)
        token_count_input = int(len(prompt_text.split()) * 1.3)
        token_count_output = random.randint(100, 300)
        is_successful = random.random() > 0.3

        return execution_time_ms, token_count_input, token_count_output, is_successful

    def generate_response(self, is_successful: bool) -> tuple[str, dict | None]:
        if is_successful:
            response_text = f"""Based on analysis:
            1. Predicted demand: {random.randint(50, 200)} units
            2. Recommended stock: {random.randint(100, 300)} units
            3. Reorder threshold: {random.randint(30, 80)} units
            4. Confidence: {random.uniform(0.7, 0.95):.2f}
            """
            parsed_response = {
                "predicted_demand": random.randint(50, 200),
                "recommended_stock": random.randint(100, 300),
                "reorder_threshold": random.randint(30, 80),
                "confidence": random.uniform(0.7, 0.95),
            }
            return response_text, parsed_response

        return "Unable to provide recommendation due to insufficient data.", None

    def create_metadata(
        self,
        product_id: str,
        execution_time_ms: float,
        token_count_input: int,
        token_count_output: int,
    ) -> PromptMetadata:
        cost_usd = (token_count_input * 0.00015 + token_count_output * 0.0006) / 1000

        return PromptMetadata(
            model_name=OpenAIModel.GPT_5_4_MINI,
            temperature=0.3,
            use_case=f"Inventory optimization for product {product_id}",
            category=PromptCategory.DATA_EXTRACTION,
            tags=["inventory", "demand_forecasting", "optimization", "autonomous_agent"],
            execution_time_ms=execution_time_ms,
            token_count_input=token_count_input,
            token_count_output=token_count_output,
            cost_usd=cost_usd,
            user_id="agent_inventory_optimizer",
            session_id=self.session_id,
        )

    def create_evaluation(
        self,
        is_successful: bool,
        parsed_response: dict | None,
    ) -> tuple[EvaluationCriteria, EvaluationStatus, str | None]:
        if is_successful and parsed_response:
            confidence = parsed_response.get("confidence", 0.5)
            evaluation = EvaluationCriteria(
                accuracy=min(confidence + random.uniform(-0.1, 0.1), 1.0),
                completeness=1.0,
                relevance=random.uniform(0.85, 0.98),
                task_completed=True,
            )
            return evaluation, EvaluationStatus.SUCCESS, None

        evaluation = EvaluationCriteria(
            accuracy=random.uniform(0.2, 0.4),
            completeness=0.0,
            relevance=0.5,
            task_completed=False,
            error_count=1,
        )
        failure_reason = "Insufficient historical data for accurate prediction"
        return evaluation, EvaluationStatus.FAILURE, failure_reason

    async def analyze_demand_pattern(self, product_id: str, historical_data: dict) -> dict:
        prompt_text = self.generate_prompt_text(product_id, historical_data)
        messages = self.create_messages(prompt_text)

        execution_time_ms, token_count_input, token_count_output, is_successful = self.simulate_execution(prompt_text)

        response_text, parsed_response = self.generate_response(is_successful)

        metadata = self.create_metadata(
            product_id,
            execution_time_ms,
            token_count_input,
            token_count_output,
        )

        log_id = self.prompt_service.log_prompt_execution(
            prompt_text=prompt_text,
            messages=messages,
            response_text=response_text,
            metadata=metadata,
            parsed_response=parsed_response,
        )

        evaluation, status, failure_reason = self.create_evaluation(
            is_successful,
            parsed_response,
        )

        self.prompt_service.evaluate_prompt(
            log_id=log_id,
            evaluation=evaluation,
            status=status,
            failure_reason=failure_reason,
        )

        return {
            "log_id": log_id,
            "success": is_successful,
            "response": parsed_response,
            "metadata": metadata,
        }


def generate_historical_data() -> dict:
    return {
        "sales_30d": random.randint(500, 2000),
        "seasonal_trend": random.choice(SEASONAL_TRENDS),
        "market_conditions": random.choice(MARKET_CONDITIONS),
    }


async def simulate_agent_operations(num_operations: int = 15) -> List[dict]:
    print_section_header(f"ADVANCED EXAMPLE: Simulating {num_operations} Agent Operations")

    prompt_service = PromptManagementService(storage_dir=STORAGE_DIR)
    agent = InventoryOptimizationAgent(prompt_service)

    results = []

    print("Running autonomous agent operations...")
    print_step_header()

    for i in range(num_operations):
        product_id = random.choice(PRODUCTS)
        historical_data = generate_historical_data()

        result = await agent.analyze_demand_pattern(product_id, historical_data)
        results.append(result)

        status_icon = "✓" if result["success"] else "✗"
        status_text = "SUCCESS" if result["success"] else "FAILED"
        print(f"{status_icon} Operation {i + 1}/{num_operations}: {product_id} - {status_text}")

        await asyncio.sleep(0.1)

    success_count = sum(1 for r in results if r["success"])
    failure_count = len(results) - success_count

    print(f"\n✓ Completed {num_operations} operations:")
    print(f"  Successes: {success_count}")
    print(f"  Failures: {failure_count}")
    print(f"  Success rate: {success_count / num_operations:.1%}")

    return results


def create_templates_from_successes(
    prompt_service: PromptManagementService,
    successful_results: List[dict],
):
    print("Creating templates from successful patterns...")
    print_step_header()

    best_results = successful_results[:3]

    for i, result in enumerate(best_results, 1):
        template = prompt_service.create_template_from_success(
            log_id=result["log_id"],
            template_name=f"inventory_demand_analysis_v{i}",
            description=f"Optimized template for demand forecasting and stock optimization (variant {i})",
            required_variables=["product_id", "sales_30d"],
            optional_variables=["seasonal_trend", "market_conditions", "promotional_events"],
        )

        if template:
            print(f"✓ Created template: {template.name}")
            print(f"  Template ID: {template.template_id}")
            print(f"  Recommended temperature: {template.recommended_temperature}")


def create_antipatterns_from_failures(
    prompt_service: PromptManagementService,
    storage_dir: Path,
    failed_results: List[dict],
):
    print("\nIdentifying anti-patterns from failures...")
    print_step_header()

    if not failed_results:
        return

    antipattern = prompt_service.create_antipattern_from_failure(
        log_id=failed_results[0]["log_id"],
        pattern_name="insufficient_data_pattern",
        failure_reason="Attempting to make predictions without sufficient historical data leads to low-confidence or failed analyses",
        recommended_fix="Ensure at least 60 days of historical data before requesting demand forecasts. If unavailable, use rule-based fallback or request more data collection.",
        severity="high",
    )

    if antipattern:
        print(f"✓ Created anti-pattern: {antipattern.name}")
        print(f"  Pattern ID: {antipattern.pattern_id}")
        print(f"  Severity: {antipattern.severity}")
        print(f"  Recommended fix: {antipattern.recommended_fix}")

        for _ in range(len(failed_results) - 1):
            analyzer = PromptAnalyzer(PromptStorage(storage_dir))
            analyzer.update_antipattern_occurrence(antipattern.pattern_id)

        print(f"  Total occurrences recorded: {len(failed_results)}")


async def analyze_patterns_and_create_templates(results: List[dict]):
    print_section_header("STEP 2: Analyzing Patterns and Creating Templates")

    prompt_service = PromptManagementService(storage_dir=STORAGE_DIR)

    successful_results = [r for r in results if r["success"]]
    failed_results = [r for r in results if not r["success"]]

    if successful_results:
        create_templates_from_successes(prompt_service, successful_results)

    if failed_results:
        create_antipatterns_from_failures(prompt_service, STORAGE_DIR, failed_results)


def display_storage_statistics(summary: dict):
    print("✓ Storage Statistics:")
    storage_stats = summary.get("storage_statistics", {})
    print(f"  Total logs: {storage_stats.get('total_logs', 0)}")
    print(f"  Total templates: {storage_stats.get('total_templates', 0)}")
    print(f"  Total anti-patterns: {storage_stats.get('total_antipatterns', 0)}")


def display_success_rates(summary: dict):
    print("\n✓ Success Rates by Category:")
    success_rates = summary.get("success_rates_by_category", {})
    for category, rate in success_rates.items():
        print(f"  {category}: {rate:.1%}")


def display_model_performance(summary: dict):
    print("\n✓ Model Performance:")
    model_perf = summary.get("model_performance", {})
    for model, stats in model_perf.items():
        print(f"  {model}:")
        print(f"    Total uses: {stats.get('total_uses', 0)}")
        print(f"    Success rate: {stats.get('success_rate', 0):.1%}")

        if stats.get("average_score"):
            print(f"    Average score: {stats.get('average_score'):.2f}")

        if stats.get("average_execution_time_ms"):
            print(f"    Avg execution time: {stats.get('average_execution_time_ms'):.0f}ms")


def display_cost_analysis(prompt_service: PromptManagementService):
    print("\nCost Analysis:")
    print_step_header()

    cost_analysis = prompt_service.get_cost_analysis()
    print(f"✓ Total API cost: ${cost_analysis.get('total_cost_usd', 0):.4f}")
    print(f"  Input tokens: {cost_analysis.get('total_input_tokens', 0):,}")
    print(f"  Output tokens: {cost_analysis.get('total_output_tokens', 0):,}")

    cost_by_cat = cost_analysis.get("cost_by_category", {})
    if cost_by_cat:
        print("\n  Cost by category:")
        for cat, cost in cost_by_cat.items():
            print(f"    {cat}: ${cost:.4f}")


def display_template_usage(analytics: PromptAnalytics):
    print("\nTemplate Usage Report:")
    print_step_header()

    template_report = analytics.get_template_usage_report()

    if template_report:
        print("✓ Top templates by usage:")
        for i, tmpl in enumerate(template_report[:5], 1):
            print(f"  {i}. {tmpl['template_name']}")
            print(f"     Uses: {tmpl['total_uses']} | Success rate: {tmpl['success_rate']:.1%}")
            if tmpl.get("average_score"):
                print(f"     Average score: {tmpl['average_score']:.2f}")


def display_antipattern_report(analytics: PromptAnalytics):
    print("\nAnti-Pattern Report:")
    print_step_header()

    antipattern_report = analytics.get_antipattern_report()
    if antipattern_report:
        print("✓ Critical anti-patterns:")
        for i, pattern in enumerate(antipattern_report[:5], 1):
            print(f"  {i}. {pattern['pattern_name']}")
            print(f"     Severity: {pattern['severity']} | Occurrences: {pattern['occurrence_count']}")
            print(f"     Fix: {pattern.get('recommended_fix', 'N/A')}")


def display_improvement_suggestions(prompt_service: PromptManagementService):
    print("\nImprovement Suggestions:")
    print_step_header()

    suggestions = prompt_service.get_improvement_suggestions()
    if suggestions:
        print(f"✓ Found {len(suggestions)} suggestion(s):")
        for i, suggestion in enumerate(suggestions[:5], 1):
            print(f"\n  {i}. [{suggestion['severity'].upper()}] {suggestion['type']}")
            print(f"     {suggestion['suggestion']}")
    else:
        print("✓ No improvement suggestions at this time. System is performing well!")


def display_success_rate_analysis(prompt_service: PromptManagementService):
    print("\nSuccess Rate Analysis:")
    print_step_header()

    success_rates_summary = prompt_service.get_success_rates()
    if not success_rates_summary:
        return

    overall_avg = sum(success_rates_summary.values()) / len(success_rates_summary)
    print(f"✓ Overall success rate: {overall_avg:.1%}")

    low_performing = {k: v for k, v in success_rates_summary.items() if v < 0.7}
    if low_performing:
        print("\n⚠  Categories needing attention:")
        for cat, rate in low_performing.items():
            print(f"   {cat}: {rate:.1%} - Consider reviewing prompts in this category")


async def generate_analytics_and_insights():
    print_section_header("STEP 3: Generating Analytics and Insights")

    prompt_service = PromptManagementService(storage_dir=STORAGE_DIR)
    analytics = PromptAnalytics(PromptStorage(STORAGE_DIR))

    print("Performance Summary:")
    print_step_header()

    summary = prompt_service.get_performance_summary()
    display_storage_statistics(summary)
    display_success_rates(summary)
    display_model_performance(summary)

    display_cost_analysis(prompt_service)
    display_template_usage(analytics)
    display_antipattern_report(analytics)
    display_improvement_suggestions(prompt_service)
    display_success_rate_analysis(prompt_service)


async def demonstrate_template_optimization():
    print_section_header("STEP 4: Template Optimization Demonstration")

    prompt_service = PromptManagementService(storage_dir=STORAGE_DIR)

    templates = prompt_service.search_templates(
        category=PromptCategory.DATA_EXTRACTION,
        tags=["inventory"],
    )

    if not templates:
        return

    template = templates[0]
    print(f"Optimizing template: {template.name}")
    print_step_header()

    print("Initial stats:")
    print(f"  Success count: {template.success_count}")
    print(f"  Failure count: {template.failure_count}")
    print(f"  Success rate: {template.get_success_rate():.1%}")

    if template.average_score:
        print(f"  Average score: {template.average_score:.2f}")
    else:
        print("  No score yet")

    print("\nSimulating template usage with feedback...")
    for i in range(5):
        success = random.random() > 0.2
        score = random.uniform(0.75, 0.95) if success else random.uniform(0.3, 0.5)

        updated = prompt_service.record_template_usage(
            template_id=template.template_id,
            success=success,
            score=score,
        )

        if updated and i == 4:
            print(f"\nUpdated stats after {i + 1} uses:")
            print(f"  Success count: {updated.success_count}")
            print(f"  Failure count: {updated.failure_count}")
            print(f"  Success rate: {updated.get_success_rate():.1%}")

            if updated.average_score:
                print(f"  Average score: {updated.average_score:.2f}")
            else:
                print("  No score yet")

    print("\n✓ Template performance is being tracked and can inform future optimizations")


def display_key_insights():
    print("\n💡 Key Insights from Advanced Example:")
    print("   1. Autonomous agents can log all prompts for systematic analysis")
    print("   2. Both successes and failures provide valuable learning opportunities")
    print("   3. Templates emerge from successful patterns and improve over time")
    print("   4. Anti-patterns prevent repeating mistakes and reduce wasted API calls")
    print("   5. Analytics provide actionable insights for cost optimization")
    print("   6. Continuous feedback loop drives systematic improvement")


def display_business_impact():
    print("\n📊 Business Impact:")
    print("   - Reduced API costs by avoiding known failure patterns")
    print("   - Improved response quality through template optimization")
    print("   - Faster development with reusable, proven prompt patterns")
    print("   - Data-driven decisions based on actual performance metrics")


async def main():
    try:
        results = await simulate_agent_operations(num_operations=15)
        await analyze_patterns_and_create_templates(results)
        await generate_analytics_and_insights()
        await demonstrate_template_optimization()

        print_section_header("ADVANCED WORKFLOW COMPLETED")
        display_key_insights()
        display_business_impact()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
