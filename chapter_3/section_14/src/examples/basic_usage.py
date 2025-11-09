"""Basic usage examples for auto-structured-output package"""

import os
from typing import Any, Optional

from src.client.llm_client import GeminiModel, OpenAIModel
from src.examples.runner import run


def example_1_simple_user_model(
    llm_client: Any,
    model: OpenAIModel | GeminiModel,
    output_directory: Optional[str] = None,
) -> None:
    """Example 1: Extract a simple user model"""
    print("\n=== Example 1: Simple User Model ===")

    prompt = """
We have collected the user’s profile information as follows.

<example>
John Doe
21 years old
johndoe@example.com
Male
Tokyo, Japan
Theme: light
No notifications
</example>

Please output the user information in the following format:
- User's name
- Age
- Email address
- Preferences
  - Theme ("light" or "dark"; default "light")
  - Whether notifications are enabled

    """

    run(
        llm_client=llm_client,
        model=model,
        prompt=prompt,
        file_name=os.path.join(output_directory, "simple_user_model.json") if output_directory else None,
    )


def example_2_product_with_enum(
    llm_client: Any,
    model: OpenAIModel | GeminiModel,
    output_directory: Optional[str] = None,
) -> None:
    """Example 2: Product model with enum status"""
    print("\n=== Example 2: Product with Enum Status ===")

    prompt = """We have the following product information.
<product>
ID: P12345
Name: Wireless Mouse
Price: 29.99
Status: available
</product>

Please output the product information in the following format:
- product_id
- name
- price: Product price (must be 0 or greater)
- status: one of "available", "out_of_stock", "discontinued"
    """

    run(
        llm_client=llm_client,
        model=model,
        prompt=prompt,
        file_name=os.path.join(output_directory, "product_with_enum.json") if output_directory else None,
    )


def example_3_optional_fields(
    llm_client: Any,
    model: OpenAIModel | GeminiModel,
    output_directory: Optional[str] = None,
) -> None:
    """Example 3: Model with optional fields"""
    print("\n=== Example 3: Optional Fields ===")

    prompt = """Analyze the following book information.
<book>
Title: The Great Gatsby
Author: F. Scott Fitzgerald
ISBN: 9780743273565
Publication Year: 1925
Rating: 4.2
Comments: A classic novel of the Jazz Age.
Reviews: 3500
</book>

Please output the book information in the following format:
- title (string, required): Book title
- author (string, required): Author name
- isbn (string, optional): ISBN number
- publication_year (integer, optional): Year published
- rating (number, optional): Rating from 0 to 5
    """

    run(
        llm_client=llm_client,
        model=model,
        prompt=prompt,
        file_name=os.path.join(output_directory, "book_with_optional_fields.json") if output_directory else None,
    )


def example_4_array_fields(
    llm_client: Any,
    model: OpenAIModel | GeminiModel,
    output_directory: Optional[str] = None,
) -> None:
    """Example 4: Model with array fields"""
    print("\n=== Example 4: Array Fields ===")

    prompt = """Review the following course information.
<course>
Course ID: CS101
Title: Introduction to Computer Science
Instructor: Dr. Smith
Topics: Programming, Algorithms, Data Structures
Prerequisites: None
</course>

Please output the course information in the following format:
course_id
title
instructor
topics
prerequisites
    """

    run(
        llm_client=llm_client,
        model=model,
        prompt=prompt,
        file_name=os.path.join(output_directory, "course_with_array_fields.json") if output_directory else None,
    )


def example_5_datetime_fields(
    llm_client: Any,
    model: OpenAIModel | GeminiModel,
    output_directory: Optional[str] = None,
) -> None:
    """Example 5: Model with date-time fields"""
    print("\n=== Example 5: DateTime Fields ===")

    prompt = """You are an expert event organizer.
Here is the event information:
<event>
Event ID: E56789
Name: Tech Conference 2024
Start Time: 2024-09-15T09:00:00Z
End Time: 2024-09-15T17:00:00Z
Location: San Francisco, CA
</event>

Please output the event information in the following format:
- event_id
- name
- start_time
- end_time
- location
    """

    run(
        llm_client=llm_client,
        model=model,
        prompt=prompt,
        file_name=os.path.join(output_directory, "event_with_datetime_fields.json") if output_directory else None,
    )
