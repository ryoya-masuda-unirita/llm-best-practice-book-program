from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from jinja2 import Environment, FileSystemLoader, Template
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from src.logger import make_logger

logger = make_logger(__name__)


class TemplateVariable(BaseModel):
    """Definition of a template variable."""

    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True,
        extra="ignore",
        arbitrary_types_allowed=True,
    )

    type: str = Field(..., description="Variable type (string, int, bool, etc.)")
    description: str = Field(..., description="Description of the variable")
    required: bool = Field(default=True, description="Whether the variable is required")
    default: Optional[Any] = Field(default=None, description="Default value if not required")


class PromptTemplate(BaseModel):
    """Structured prompt template definition."""

    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True,
        extra="ignore",
        arbitrary_types_allowed=True,
    )

    name: str = Field(..., description="Template name")
    description: str = Field(..., description="Template description")
    version: str = Field(..., description="Template version")
    variables: Dict[str, TemplateVariable] = Field(default_factory=dict, description="Template variables")
    system_prompt: str = Field(..., description="System prompt template")
    user_prompt: str = Field(..., description="User prompt template")
    assistant_prompt: Optional[str] = Field(default=None, description="Assistant prompt template")


class TemplateEngine:
    """Template engine for managing and rendering prompt templates."""

    def __init__(self, template_dir: str = "templates"):
        """Initialize template engine.

        Args:
            template_dir: Directory containing template files
        """
        self.template_dir = Path(template_dir)
        self.jinja_env = Environment(loader=FileSystemLoader(self.template_dir), trim_blocks=True, lstrip_blocks=True)
        self._templates: Dict[str, PromptTemplate] = {}
        self._load_templates()

    def _load_templates(self) -> None:
        """Load all templates from the template directory."""
        if not self.template_dir.exists():
            logger.warning(f"Template directory {self.template_dir} does not exist")
            return

        for template_file in self.template_dir.glob("*.yaml"):
            try:
                with open(template_file, "r", encoding="utf-8") as f:
                    template_data = yaml.safe_load(f)

                # Convert variables dict to TemplateVariable objects
                variables = {}
                for var_name, var_def in template_data.get("variables", {}).items():
                    variables[var_name] = TemplateVariable(**var_def)

                template_data["variables"] = variables
                template = PromptTemplate(**template_data)
                self._templates[template.name] = template
                logger.info(f"Loaded template: {template.name}")

            except (yaml.YAMLError, ValidationError) as e:
                logger.error(f"Failed to load template {template_file}: {e}")

    def get_template(self, name: str) -> Optional[PromptTemplate]:
        """Get a template by name.

        Args:
            name: Template name

        Returns:
            Template if found, None otherwise
        """
        return self._templates.get(name)

    def list_templates(self) -> List[str]:
        """List all available template names.

        Returns:
            List of template names
        """
        return list(self._templates.keys())

    def validate_variables(self, template_name: str, variables: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and process template variables.

        Args:
            template_name: Name of the template
            variables: Variables to validate

        Returns:
            Processed variables with defaults applied

        Raises:
            ValueError: If validation fails
        """
        template = self.get_template(template_name)
        if not template:
            raise ValueError(f"Template '{template_name}' not found")

        processed_vars = {}

        # Check required variables and apply defaults
        for var_name, var_def in template.variables.items():
            if var_name in variables:
                processed_vars[var_name] = variables[var_name]
            elif var_def.required:
                raise ValueError(f"Required variable '{var_name}' is missing")
            elif var_def.default is not None:
                processed_vars[var_name] = var_def.default

        # Add any extra variables that were provided
        for var_name, value in variables.items():
            if var_name not in processed_vars:
                processed_vars[var_name] = value

        return processed_vars

    def render_template(self, template_name: str, variables: Dict[str, Any]) -> List[Dict[str, str]]:
        """Render a template with the given variables.

        Args:
            template_name: Name of the template to render
            variables: Variables to inject into the template

        Returns:
            List of message dictionaries for LLM API

        Raises:
            ValueError: If template not found or rendering fails
        """
        template = self.get_template(template_name)
        if not template:
            raise ValueError(f"Template '{template_name}' not found")

        # Validate and process variables
        processed_vars = self.validate_variables(template_name, variables)

        try:
            # Render system prompt
            system_template = Template(template.system_prompt)
            system_content = system_template.render(**processed_vars)

            # Render user prompt
            user_template = Template(template.user_prompt)
            user_content = user_template.render(**processed_vars)

            messages = [{"role": "system", "content": system_content}, {"role": "user", "content": user_content}]

            # Add assistant prompt if present
            if template.assistant_prompt:
                assistant_template = Template(template.assistant_prompt)
                assistant_content = assistant_template.render(**processed_vars)
                messages.append({"role": "assistant", "content": assistant_content})

            return messages

        except Exception as e:
            logger.error(f"Failed to render template '{template_name}': {e}")
            raise ValueError(f"Template rendering failed: {e}")

    def reload_templates(self) -> None:
        """Reload all templates from disk."""
        self._templates.clear()
        self._load_templates()
        logger.info("Templates reloaded")

    def load_variables_from_file(self, file_path: str) -> Dict[str, Any]:
        """Load variables from a YAML file.

        Args:
            file_path: Path to the YAML variable file

        Returns:
            Dictionary of variables loaded from the file

        Raises:
            ValueError: If file cannot be loaded or parsed
        """
        try:
            file_path_obj = Path(file_path)
            if not file_path_obj.exists():
                raise ValueError(f"Variable file '{file_path}' does not exist")

            with open(file_path_obj, "r", encoding="utf-8") as f:
                variables = yaml.safe_load(f) or {}

            logger.info(f"Loaded variables from {file_path}: {list(variables.keys())}")
            return variables

        except yaml.YAMLError as e:
            logger.error(f"Failed to parse YAML file '{file_path}': {e}")
            raise ValueError(f"Invalid YAML file: {e}")
        except Exception as e:
            logger.error(f"Failed to load variable file '{file_path}': {e}")
            raise ValueError(f"Could not load variable file: {e}")

    def list_variable_files(self, variables_dir: str = "variables") -> List[str]:
        """List all available variable files.

        Args:
            variables_dir: Directory containing variable files

        Returns:
            List of variable file names (without .yaml extension)
        """
        variables_path = Path(variables_dir)
        if not variables_path.exists():
            return []

        variable_files = []
        for file_path in variables_path.glob("*.yaml"):
            variable_files.append(file_path.stem)

        return sorted(variable_files)


# Global template engine instance
template_engine = TemplateEngine()
