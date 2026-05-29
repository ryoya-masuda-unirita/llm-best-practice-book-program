"""Template engine for structured prompt management using Jinja2."""

from pathlib import Path
from typing import Any

import yaml
from jinja2 import Environment, FileSystemLoader, TemplateNotFound, meta


class TemplateValidationError(Exception):
    """Raised when template validation fails."""

    pass


class TemplateEngine:
    """Template engine for loading and rendering YAML-based prompt templates."""

    def __init__(self, template_dir: str | Path = "templates"):
        self.template_dir = Path(template_dir)
        if not self.template_dir.exists():
            raise FileNotFoundError(f"Template directory not found: {self.template_dir}")

        self.env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
        )

    def get_template_variables(self, template_name: str) -> set[str]:
        """Extract all variables used in a template."""
        try:
            template_source = self.env.loader.get_source(self.env, template_name)[0]
            parsed_content = self.env.parse(template_source)
            return meta.find_undeclared_variables(parsed_content)
        except TemplateNotFound:
            raise TemplateNotFound(f"Template not found: {template_name}")

    def validate_variables(self, template_name: str, variables: dict[str, Any]) -> None:
        """Validate that all required variables are provided for a template."""
        required_vars = self.get_template_variables(template_name)
        provided_vars = set(variables.keys())
        missing_vars = required_vars - provided_vars

        if missing_vars:
            raise TemplateValidationError(f"Missing required variables for template '{template_name}': {missing_vars}")

    def render_template(self, template_name: str, variables: dict[str, Any], validate: bool = True) -> dict[str, str]:
        """Render a YAML template with the provided variables."""
        if validate:
            self.validate_variables(template_name, variables)

        template = self.env.get_template(template_name)
        rendered_yaml = template.render(**variables)

        return yaml.safe_load(rendered_yaml)

    def render_prompt_messages(
        self,
        template_name: str,
        variables: dict[str, Any],
        system_key: str = "system_prompt",
        user_key: str = "user_prompt",
        validate: bool = True,
    ) -> list[dict[str, str]]:
        """Render a template and convert it to LLM API message format."""
        rendered = self.render_template(template_name, variables, validate=validate)

        if system_key not in rendered:
            raise TemplateValidationError(f"Template missing key: {system_key}")
        if user_key not in rendered:
            raise TemplateValidationError(f"Template missing key: {user_key}")

        return [
            {"role": "system", "content": rendered[system_key]},
            {"role": "user", "content": rendered[user_key]},
        ]
