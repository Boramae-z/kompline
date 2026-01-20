"""Input guardrails for validating source code submissions."""

import ast
from dataclasses import dataclass
from typing import Any

from agents import input_guardrail, GuardrailFunctionOutput


@dataclass
class ValidationResult:
    """Result of input validation."""

    valid: bool
    errors: list[str]
    warnings: list[str]
    metadata: dict[str, Any]


def validate_python_source(source_code: str) -> ValidationResult:
    """Validate that the input is valid Python source code.

    Args:
        source_code: The source code to validate.

    Returns:
        ValidationResult with validation status and details.
    """
    errors = []
    warnings = []
    metadata = {}

    # Check if empty
    if not source_code or not source_code.strip():
        errors.append("Source code is empty")
        return ValidationResult(False, errors, warnings, metadata)

    # Check length limits
    if len(source_code) > 100000:  # 100KB limit
        errors.append("Source code exceeds maximum length (100KB)")
        return ValidationResult(False, errors, warnings, metadata)

    if len(source_code) < 10:
        warnings.append("Source code is very short")

    # Try to parse as Python
    try:
        tree = ast.parse(source_code)
        metadata["ast_valid"] = True
        metadata["node_count"] = len(list(ast.walk(tree)))
    except SyntaxError as e:
        errors.append(f"Invalid Python syntax: {e.msg} at line {e.lineno}")
        return ValidationResult(False, errors, warnings, metadata)

    # Check for potentially dangerous patterns
    dangerous_patterns = [
        ("exec(", "Use of exec() detected - potential security risk"),
        ("eval(", "Use of eval() detected - potential security risk"),
        ("__import__", "Dynamic import detected"),
        ("subprocess", "Subprocess usage detected"),
        ("os.system", "System command execution detected"),
    ]

    source_lower = source_code.lower()
    for pattern, message in dangerous_patterns:
        if pattern.lower() in source_lower:
            warnings.append(message)

    # Count lines and functions
    lines = source_code.splitlines()
    metadata["line_count"] = len(lines)
    metadata["has_functions"] = any(
        isinstance(node, ast.FunctionDef) for node in ast.walk(tree)
    )
    metadata["has_classes"] = any(
        isinstance(node, ast.ClassDef) for node in ast.walk(tree)
    )

    return ValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        metadata=metadata,
    )


@input_guardrail
async def source_code_guardrail(
    ctx,
    agent,
    input_data: str,
) -> GuardrailFunctionOutput:
    """Guardrail to validate source code input.

    Args:
        ctx: The run context.
        agent: The agent receiving the input.
        input_data: The input string to validate.

    Returns:
        GuardrailFunctionOutput indicating whether to proceed.
    """
    # Extract source code from input if it's a structured message
    if isinstance(input_data, str):
        # Look for code blocks
        if "```python" in input_data:
            start = input_data.find("```python") + 9
            end = input_data.find("```", start)
            if end > start:
                source_code = input_data[start:end].strip()
            else:
                source_code = input_data
        elif "```" in input_data:
            start = input_data.find("```") + 3
            end = input_data.find("```", start)
            if end > start:
                source_code = input_data[start:end].strip()
            else:
                source_code = input_data
        else:
            source_code = input_data
    else:
        source_code = str(input_data)

    result = validate_python_source(source_code)

    if not result.valid:
        return GuardrailFunctionOutput(
            output_info={"errors": result.errors},
            tripwire_triggered=True,
        )

    return GuardrailFunctionOutput(
        output_info={
            "valid": True,
            "warnings": result.warnings,
            "metadata": result.metadata,
        },
        tripwire_triggered=False,
    )


# Alias for import
SourceCodeGuardrail = source_code_guardrail
