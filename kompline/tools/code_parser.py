"""Code parsing tools for analyzing Python source code."""

import ast
from dataclasses import dataclass
from typing import Any

try:
    from agents import function_tool
except ImportError:
    def function_tool(func):
        """Fallback decorator when agents SDK not installed."""
        func.func = func
        return func


@dataclass
class FunctionInfo:
    """Information about a parsed function."""

    name: str
    lineno: int
    args: list[str]
    returns: str | None
    docstring: str | None
    body_summary: str


@dataclass
class DataFlowInfo:
    """Information about data flow in code."""

    variables: dict[str, list[int]]  # variable -> lines where used
    function_calls: list[tuple[str, int]]  # (function_name, line)
    assignments: list[tuple[str, int, str]]  # (variable, line, value_type)


@dataclass
class CodeAnalysisResult:
    """Result of code analysis."""

    functions: list[FunctionInfo]
    data_flow: DataFlowInfo
    patterns: list[str]
    issues: list[str]


class CodeVisitor(ast.NodeVisitor):
    """AST visitor for extracting code information."""

    def __init__(self):
        self.functions: list[FunctionInfo] = []
        self.variables: dict[str, list[int]] = {}
        self.function_calls: list[tuple[str, int]] = []
        self.assignments: list[tuple[str, int, str]] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        args = [arg.arg for arg in node.args.args]
        returns = None
        if node.returns:
            returns = ast.unparse(node.returns)

        docstring = ast.get_docstring(node)
        body_lines = [ast.unparse(stmt) for stmt in node.body[:3]]
        body_summary = "; ".join(body_lines)[:200]

        self.functions.append(
            FunctionInfo(
                name=node.name,
                lineno=node.lineno,
                args=args,
                returns=returns,
                docstring=docstring,
                body_summary=body_summary,
            )
        )
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Name):
            self.function_calls.append((node.func.id, node.lineno))
        elif isinstance(node.func, ast.Attribute):
            self.function_calls.append((node.func.attr, node.lineno))
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        if node.id not in self.variables:
            self.variables[node.id] = []
        self.variables[node.id].append(node.lineno)
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        for target in node.targets:
            if isinstance(target, ast.Name):
                value_type = type(node.value).__name__
                self.assignments.append((target.id, node.lineno, value_type))
        self.generic_visit(node)


def _detect_patterns(tree: ast.AST, source: str) -> list[str]:
    """Detect common patterns in code."""
    patterns = set()
    source_lower = source.lower()

    # Text-based pattern detection
    keyword_patterns = [
        (["sort", "sorted"], "SORTING_ALGORITHM"),
        (["weight", "factor"], "WEIGHTED_CALCULATION"),
        (["rank", "score"], "RANKING_LOGIC"),
        (["filter"], "FILTERING_LOGIC"),
        (["random"], "RANDOMIZATION"),
    ]
    for keywords, pattern_name in keyword_patterns:
        if any(kw in source_lower for kw in keywords):
            patterns.add(pattern_name)

    # AST-based pattern detection
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare):
            patterns.add("COMPARISON_LOGIC")
        elif isinstance(node, ast.If):
            patterns.add("CONDITIONAL_LOGIC")

    return list(patterns)


def _detect_issues(tree: ast.AST, source: str) -> list[str]:
    """Detect potential compliance issues."""
    issues = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute) and node.func.attr == "shuffle":
                issues.append("POTENTIAL_RANDOM_ORDERING: shuffle() detected")

    source_lower = source.lower()
    hardcoded_keywords = ["priority", "preferred", "promoted", "sponsored"]
    for kw in hardcoded_keywords:
        if kw in source_lower:
            issues.append(f"POTENTIAL_BIAS: '{kw}' keyword found")

    return issues


def _parse_python_code_impl(source_code: str) -> dict[str, Any]:
    """Parse Python source code and extract structural information.

    Args:
        source_code: The Python source code to parse.

    Returns:
        Dictionary containing parsed code information including functions,
        variables, and detected patterns.
    """
    try:
        tree = ast.parse(source_code)
    except SyntaxError as e:
        return {"error": f"Syntax error: {e}", "success": False}

    visitor = CodeVisitor()
    visitor.visit(tree)

    patterns = _detect_patterns(tree, source_code)
    issues = _detect_issues(tree, source_code)

    return {
        "success": True,
        "functions": [
            {
                "name": f.name,
                "lineno": f.lineno,
                "args": f.args,
                "returns": f.returns,
                "docstring": f.docstring,
                "body_summary": f.body_summary,
            }
            for f in visitor.functions
        ],
        "data_flow": {
            "variables": visitor.variables,
            "function_calls": visitor.function_calls,
            "assignments": visitor.assignments,
        },
        "patterns": patterns,
        "issues": issues,
        "line_count": len(source_code.splitlines()),
    }


@function_tool
def parse_python_code(source_code: str) -> dict[str, Any]:
    """Parse Python source code and extract structural information.

    Args:
        source_code: The Python source code to parse.

    Returns:
        Dictionary containing parsed code information including functions,
        variables, and detected patterns.
    """
    return _parse_python_code_impl(source_code)


@function_tool
def extract_functions(source_code: str) -> list[dict[str, Any]]:
    """Extract function definitions from Python source code.

    Args:
        source_code: The Python source code to analyze.

    Returns:
        List of function information dictionaries.
    """
    result = parse_python_code(source_code)
    if not result.get("success"):
        return []
    return result.get("functions", [])


@function_tool
def analyze_data_flow(source_code: str, focus_variable: str | None = None) -> dict[str, Any]:
    """Analyze data flow in Python source code.

    Args:
        source_code: The Python source code to analyze.
        focus_variable: Optional variable name to focus analysis on.

    Returns:
        Dictionary containing data flow analysis results.
    """
    result = parse_python_code(source_code)
    if not result.get("success"):
        return {"error": result.get("error"), "success": False}

    data_flow = result.get("data_flow", {})

    if focus_variable:
        focused = {
            "variable": focus_variable,
            "usage_lines": data_flow.get("variables", {}).get(focus_variable, []),
            "assignments": [
                a for a in data_flow.get("assignments", []) if a[0] == focus_variable
            ],
        }
        return {"success": True, "focused_analysis": focused, "full_data_flow": data_flow}

    return {"success": True, "data_flow": data_flow}
