"""
Basic Example: Prompt Logging and Template Creation

This example demonstrates the fundamental workflow:
1. Log a prompt execution with metadata
2. Evaluate the result
3. Create a reusable template from successful prompts
4. Reuse templates for consistent results

Use Case: Character generation for game development
"""

import asyncio
from pathlib import Path

from src.client.llm_client import OpenAIModel
from src.model.prompt_log import (
    EvaluationCriteria,
    EvaluationStatus,
    PromptCategory,
    PromptMetadata,
)
from src.service.prompt_service import PromptManagementService
from src.service.request_llm import request_openai
from src.service.template_engine import TemplateEngine

PROJECT_ROOT = Path(__file__).parent.parent.parent
TEMPLATE_DIR = PROJECT_ROOT / "templates"
VARIABLES_DIR = PROJECT_ROOT / "variables"
STORAGE_DIR = PROJECT_ROOT / "prompt_storage"


def print_section_header(title: str):
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80 + "\n")


def print_step_header(step_number: int, title: str):
    print(f"\nStep {step_number}: {title}")
    print("-" * 80)


async def execute_character_generation(
    prompt_service: PromptManagementService,
    template_engine: TemplateEngine,
):
    print_step_header(1, "Executing prompt with character generation template...")

    template_path = TEMPLATE_DIR / "character_generation.yaml"
    variables_path = VARIABLES_DIR / "warrior.yaml"

    result = await request_openai(
        model=OpenAIModel.GPT_4O_MINI,
        template_path=template_path,
        variables_path=variables_path,
        template_dir=TEMPLATE_DIR,
        variables_dir=VARIABLES_DIR,
        template_engine=template_engine,
    )

    print(f"✓ Generated character: {result.first_name} {result.last_name}")
    print(f"  Gender: {result.gender}")
    print(f"  Age: {result.age}")
    print(f"  Personality: {result.personalities[0].short_personality if result.personalities else 'N/A'}")

    return result


def log_prompt_execution(
    prompt_service: PromptManagementService,
    result,
) -> str:
    print_step_header(2, "Logging prompt execution...")

    metadata = PromptMetadata(
        model_name=OpenAIModel.GPT_4O_MINI,
        temperature=1.0,
        use_case="RPG character generation for fantasy game",
        category=PromptCategory.CHARACTER_GENERATION,
        tags=["rpg", "fantasy", "character", "warrior"],
        user_id="game_dev_001",
    )

    log_id = prompt_service.log_prompt_execution(
        prompt_text="Generate a fantasy RPG character with warrior archetype",
        messages=[
            {"role": "system", "content": "You are a creative RPG character designer."},
            {"role": "user", "content": "Create a male warrior character, age 25, who is adventurous and curious."},
        ],
        response_text=str(result.model_dump()),
        metadata=metadata,
        parsed_response=result.model_dump(),
        template_name="character_generation.yaml",
        template_version="1.0.0",
    )

    print(f"✓ Logged execution with ID: {log_id}")
    return log_id


def evaluate_prompt_result(
    prompt_service: PromptManagementService,
    log_id: str,
):
    print_step_header(3, "Evaluating the prompt result...")

    evaluation = EvaluationCriteria(
        accuracy=0.95,
        completeness=1.0,
        relevance=0.92,
        user_feedback=True,
        task_completed=True,
    )

    updated_log = prompt_service.evaluate_prompt(
        log_id=log_id,
        evaluation=evaluation,
        status=EvaluationStatus.SUCCESS,
    )

    if updated_log:
        overall_score = updated_log.get_overall_score()
        print("✓ Evaluation completed")
        print(f"  Overall score: {overall_score:.2%}")
        print(f"  Status: {updated_log.evaluation_status}")


def create_reusable_template(
    prompt_service: PromptManagementService,
    log_id: str,
):
    print_step_header(4, "Creating reusable template from successful prompt...")

    template = prompt_service.create_template_from_success(
        log_id=log_id,
        template_name="warrior_character_template",
        description="Template for generating warrior-type RPG characters with consistent quality",
        required_variables=["gender", "age"],
        optional_variables=["additional_instructions", "background_story"],
    )

    if template:
        print(f"✓ Created template: {template.name}")
        print(f"  Template ID: {template.template_id}")
        print(f"  Category: {template.category}")
        print(f"  Success rate: {template.get_success_rate():.1%}")
        print(f"  Tags: {', '.join(template.tags)}")


def search_templates(prompt_service: PromptManagementService):
    print_step_header(5, "Searching for related templates...")

    templates = prompt_service.search_templates(
        category=PromptCategory.CHARACTER_GENERATION,
        tags=["warrior"],
        min_success_rate=0.8,
    )

    print(f"✓ Found {len(templates)} template(s) matching criteria:")
    for template in templates:
        print(f"  - {template.name} (success rate: {template.get_success_rate():.1%})")


def display_catalog_summary(prompt_service: PromptManagementService):
    print_step_header(6, "Viewing catalog summary...")

    summary = prompt_service.get_catalog_summary()
    print("✓ Catalog Summary:")
    print(f"  Total templates: {summary['total_templates']}")
    print(f"  Total anti-patterns: {summary['total_antipatterns']}")
    print(f"  Total template uses: {summary['total_template_uses']}")
    print(f"  Average success rate: {summary['average_success_rate']:.1%}")


async def basic_workflow():
    print_section_header("BASIC EXAMPLE: Prompt Logging and Template Creation")

    prompt_service = PromptManagementService(storage_dir=STORAGE_DIR)
    template_engine = TemplateEngine(template_dir=TEMPLATE_DIR)

    result = await execute_character_generation(prompt_service, template_engine)
    log_id = log_prompt_execution(prompt_service, result)
    evaluate_prompt_result(prompt_service, log_id)
    create_reusable_template(prompt_service, log_id)
    search_templates(prompt_service)
    display_catalog_summary(prompt_service)

    print("\n" + "=" * 80)
    print("Basic workflow completed successfully!")
    print("=" * 80 + "\n")


def display_template_details(template, index: int):
    print(f"\n{index}. {template.name}")
    print(f"   Description: {template.description}")
    print(f"   Success rate: {template.get_success_rate():.1%}")

    if template.average_score:
        print(f"   Average score: {template.average_score:.2f}")
    else:
        print("   No score yet")

    print(f"   Required variables: {', '.join(template.required_variables)}")
    print(f"   Recommended models: {', '.join(template.recommended_models)}")
    print(f"   Recommended temperature: {template.recommended_temperature}")


async def demonstrate_template_reuse():
    print_section_header("BONUS: Template Reuse Demonstration")

    prompt_service = PromptManagementService(storage_dir=STORAGE_DIR)

    recommendations = prompt_service.get_recommended_templates(
        category=PromptCategory.CHARACTER_GENERATION,
        tags=["warrior"],
        limit=3,
    )

    print(f"✓ Found {len(recommendations)} recommended template(s):")
    for index, template in enumerate(recommendations, 1):
        display_template_details(template, index)

    if recommendations:
        template_id = recommendations[0].template_id
        exported = prompt_service.export_template(template_id)

        if exported:
            print(f"\n✓ Exported template '{exported['name']}' for team sharing:")
            print(f"   Use cases: {', '.join(exported['use_case_examples'])}")

    print("\n" + "=" * 80)
    print("Template reuse demonstration completed!")
    print("=" * 80 + "\n")


def display_key_takeaways():
    print("\n💡 Key Takeaways:")
    print("   1. Every prompt execution is logged with rich metadata")
    print("   2. Results are evaluated based on predefined criteria")
    print("   3. Successful prompts become reusable templates")
    print("   4. Templates can be searched and shared across the team")
    print("   5. This creates a knowledge base that improves over time")


async def main():
    try:
        await basic_workflow()
        await demonstrate_template_reuse()
        display_key_takeaways()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
