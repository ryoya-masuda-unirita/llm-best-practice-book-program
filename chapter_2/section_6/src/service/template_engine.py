"""Template engine for structured prompt management using Jinja2."""

from pathlib import Path
from typing import Any

import yaml
from jinja2 import Environment, FileSystemLoader, TemplateNotFound, meta


class TemplateValidationError(Exception):
    """Raised when template validation fails."""

    pass


class TemplateEngine:
    """
    Template engine for loading and rendering YAML-based prompt templates.

    This class implements structured template prompting by:
    1. Loading YAML templates from a designated directory
    2. Rendering templates with dynamic variables using Jinja2
    3. Validating that all required variables are provided
    """

    def __init__(self, template_dir: str | Path = "templates"):
        """
        Initialize the template engine.

        Args:
            template_dir: Directory containing template files (default: "templates")
        """
        self.template_dir = Path(template_dir)
        if not self.template_dir.exists():
            raise FileNotFoundError(f"Template directory not found: {self.template_dir}")

        # Setup Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
        )

    def get_template_variables(self, template_name: str) -> set[str]:
        """
        Extract all variables used in a template.

        Args:
            template_name: Name of the template file

        Returns:
            Set of variable names used in the template

        Raises:
            TemplateNotFound: If template file doesn't exist
        """
        try:
            template_source = self.env.loader.get_source(self.env, template_name)[0]
            parsed_content = self.env.parse(template_source)
            return meta.find_undeclared_variables(parsed_content)
        except TemplateNotFound:
            raise TemplateNotFound(f"Template not found: {template_name}")

    def validate_variables(self, template_name: str, variables: dict[str, Any]) -> None:
        """
        Validate that all required variables are provided for a template.

        Args:
            template_name: Name of the template file
            variables: Dictionary of variables to render the template

        Raises:
            TemplateValidationError: If required variables are missing
        """
        required_vars = self.get_template_variables(template_name)
        provided_vars = set(variables.keys())
        missing_vars = required_vars - provided_vars

        if missing_vars:
            raise TemplateValidationError(f"Missing required variables for template '{template_name}': {missing_vars}")

    def render_template(self, template_name: str, variables: dict[str, Any], validate: bool = True) -> dict[str, str]:
        """
        Render a YAML template with the provided variables.

        Args:
            template_name: Name of the template file (e.g., 'character_generation.yaml')
            variables: Dictionary of variables to inject into the template
            validate: Whether to validate that all required variables are provided (default: True)

        Returns:
            Dictionary containing the rendered template data

        Raises:
            TemplateNotFound: If template file doesn't exist
            TemplateValidationError: If required variables are missing (when validate=True)
        """
        # Validate variables if requested
        if validate:
            self.validate_variables(template_name, variables)

        # Load and render the template
        template = self.env.get_template(template_name)
        rendered_yaml = template.render(**variables)

        # Parse the rendered YAML
        return yaml.safe_load(rendered_yaml)

    def render_prompt_messages(
        self,
        template_name: str,
        variables: dict[str, Any],
        system_key: str = "system_prompt",
        user_key: str = "user_prompt",
        validate: bool = True,
    ) -> list[dict[str, str]]:
        """
        Render a template and convert it to LLM API message format.

        Args:
            template_name: Name of the template file
            variables: Dictionary of variables to inject into the template
            system_key: Key in YAML for system prompt (default: 'system_prompt')
            user_key: Key in YAML for user prompt (default: 'user_prompt')
            validate: Whether to validate variables (default: True)

        Returns:
            List of message dictionaries in format [{"role": "system", "content": "..."}, ...]

        Raises:
            TemplateNotFound: If template file doesn't exist
            TemplateValidationError: If required variables are missing or keys don't exist
        """
        rendered = self.render_template(template_name, variables, validate=validate)

        # Validate that the expected keys exist
        if system_key not in rendered:
            raise TemplateValidationError(f"Template missing key: {system_key}")
        if user_key not in rendered:
            raise TemplateValidationError(f"Template missing key: {user_key}")

        return [
            {"role": "system", "content": rendered[system_key]},
            {"role": "user", "content": rendered[user_key]},
        ]
