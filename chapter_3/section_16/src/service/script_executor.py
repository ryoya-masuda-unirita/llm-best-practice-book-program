import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from src.logger import make_logger
from src.model.model import ScriptExecutionResult

logger = make_logger(__name__)

FORBIDDEN_PATTERNS = [
    r"\bopen\s*\(",
    r"\bos\.",
    r"\bpathlib\b",
    r"\bsubprocess\b",
    r"\bos\.system\b",
    r"\brequests\b",
    r"\burllib\b",
    r"\bsocket\b",
    r"\bhttp\b",
    r"\beval\s*\(",
    r"\bexec\s*\(",
    r"\bcompile\s*\(",
    r"\b__import__\s*\(",
    r"\bimportlib\b",
    r"\bgetattr\s*\(",
    r"\bsetattr\s*\(",
    r"\bdelattr\s*\(",
    r"\bglobals\s*\(",
    r"\blocals\s*\(",
    r"\bvars\s*\(",
    r"\bbreakpoint\s*\(",
    r"\binput\s*\(",
]

ALLOWED_IMPORTS = {"sys", "json", "re"}


def validate_script(script: str) -> tuple[bool, str]:
    """Validate the script for security issues."""
    for pattern in FORBIDDEN_PATTERNS:
        if re.search(pattern, script):
            return False, f"Forbidden pattern detected: {pattern}"

    import_pattern = r"^\s*(?:from\s+(\w+)|import\s+(\w+))"
    for line in script.split("\n"):
        match = re.match(import_pattern, line)
        if match:
            module = match.group(1) or match.group(2)
            if module and module not in ALLOWED_IMPORTS:
                return False, f"Forbidden import: {module}"

    return True, ""


def execute_script(script: str, document_content: str, timeout: int = 30) -> ScriptExecutionResult:
    """Execute the generated script in a sandboxed environment."""
    is_valid, error_message = validate_script(script)
    if not is_valid:
        logger.warning(f"Script validation failed: {error_message}")
        return ScriptExecutionResult(
            success=False,
            output="",
            error=f"Security validation failed: {error_message}",
            result=None,
        )

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as script_file:
        script_file.write(script)
        script_path = script_file.name

    try:
        result = subprocess.run(
            [sys.executable, script_path],
            input=document_content,
            capture_output=True,
            text=True,
            timeout=timeout,
            env={"PATH": "", "HOME": "", "PYTHONPATH": ""},
        )

        stdout = result.stdout.strip()
        stderr = result.stderr.strip()

        if result.returncode != 0:
            logger.warning(f"Script execution failed with return code {result.returncode}")
            return ScriptExecutionResult(
                success=False,
                output=stdout,
                error=stderr,
                result=None,
            )

        try:
            parsed_result = json.loads(stdout)
            return ScriptExecutionResult(
                success=True,
                output=stdout,
                error="",
                result=parsed_result,
            )
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse script output as JSON: {e}")
            return ScriptExecutionResult(
                success=False,
                output=stdout,
                error=f"Invalid JSON output: {e}",
                result=None,
            )

    except subprocess.TimeoutExpired:
        logger.warning("Script execution timed out")
        return ScriptExecutionResult(
            success=False,
            output="",
            error=f"Execution timed out after {timeout} seconds",
            result=None,
        )
    except Exception as e:
        logger.error(f"Script execution error: {e}")
        return ScriptExecutionResult(
            success=False,
            output="",
            error=str(e),
            result=None,
        )
    finally:
        Path(script_path).unlink(missing_ok=True)
