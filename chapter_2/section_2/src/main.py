import asyncio
import os
from functools import wraps

import click
from src.client.llm_client import OpenAIModel, openai_client
from src.examples.advanced_examples import (
    example_1_nested_objects,
    example_2_complex_article,
    example_3_array_of_objects,
    example_4_deep_nesting,
    example_5_anyof_union_types,
    example_6_validation_constraints,
)
from src.examples.basic_usage import (
    example_1_simple_user_model,
    example_2_product_with_enum,
    example_3_optional_fields,
    example_4_array_fields,
    example_5_datetime_fields,
)
from src.examples.high_reasoning_examples import (
    example_1_customer_feedback_analysis,
    example_2_meeting_summary,
    example_3_research_paper_metadata,
    example_4_job_application_evaluation,
    example_5_financial_transaction_analysis,
    example_6_high_reasoning,
)
from src.logger import make_logger

logger = make_logger(__name__)

examples = {
    "example_1_simple_user_model": example_1_simple_user_model,
    "example_2_product_with_enum": example_2_product_with_enum,
    "example_3_optional_fields": example_3_optional_fields,
    "example_4_array_fields": example_4_array_fields,
    "example_5_datetime_fields": example_5_datetime_fields,
    "example_1_nested_objects": example_1_nested_objects,
    "example_2_complex_article": example_2_complex_article,
    "example_3_array_of_objects": example_3_array_of_objects,
    "example_4_deep_nesting": example_4_deep_nesting,
    "example_5_anyof_union_types": example_5_anyof_union_types,
    "example_6_validation_constraints": example_6_validation_constraints,
    "example_1_customer_feedback_analysis": example_1_customer_feedback_analysis,
    "example_2_meeting_summary": example_2_meeting_summary,
    "example_3_research_paper_metadata": example_3_research_paper_metadata,
    "example_4_job_application_evaluation": example_4_job_application_evaluation,
    "example_5_financial_transaction_analysis": example_5_financial_transaction_analysis,
    "example_6_high_reasoning": example_6_high_reasoning,
}


def async_cmd(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        return asyncio.run(func(*args, **kwargs))

    return wrapper


@click.command()
@click.option(
    "--model",
    "-m",
    type=click.Choice(OpenAIModel.list_str()),
    required=True,
    help="The model to use for the request.",
)
@click.option(
    "--example",
    "-e",
    type=click.Choice(list(examples.keys())),
    required=False,
    help="The example to run.",
)
@click.option(
    "--output-directory",
    "-od",
    type=click.Path(),
    required=False,
    default="outputs",
    help="The directory to save output files.",
)
@async_cmd
async def main(
    model: str,
    example: str,
    output_directory: str = "outputs",
):
    """Run auto-structured output examples

    This command executes examples from src/examples/ directory.
    Each example demonstrates the two-step auto-structured output approach.
    """

    os.makedirs(output_directory, exist_ok=True)

    logger.info(f"Executing example: {example}")
    examples[example](
        llm_client=openai_client,
        model=model,
        output_directory=output_directory,
    )


if __name__ == "__main__":
    main()
