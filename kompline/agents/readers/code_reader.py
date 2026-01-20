"""Code Reader Agent for extracting evidence from source code."""

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents import Agent

from kompline.agents.readers.base_reader import BaseReader
from kompline.models import (
    Artifact,
    ArtifactType,
    EvidenceCollection,
    EvidenceRequirement,
    EvidenceType,
    Provenance,
)
from kompline.tools.code_parser import (
    _parse_python_code_impl,
    analyze_data_flow,
    extract_functions,
    parse_python_code,
)

CODE_READER_INSTRUCTIONS = """You are the Code Reader Agent for Kompline.

Your role is to extract evidence from Python source code for compliance auditing.

## What to Extract

Based on evidence requirements, extract:
1. **Function definitions**: Signatures, docstrings, bodies
2. **Algorithm patterns**: Sorting, ranking, filtering, weighting logic
3. **Data flow**: How data moves through the code
4. **Potential issues**: Undocumented weights, hidden preferences, bias patterns

## Tools Available

- `parse_python_code`: Full code analysis including patterns and issues
- `extract_functions`: List all functions with signatures
- `analyze_data_flow`: Track variable usage and assignments

## Output Format

For each piece of evidence, provide:
- Source file and line number(s)
- The relevant code snippet
- Why this is relevant to the compliance check
- Any patterns or issues detected

## Important Guidelines

- Include exact line numbers for all findings
- Quote code exactly as it appears
- Flag any suspicious patterns that might affect algorithm fairness
- Note both compliant AND non-compliant patterns
"""


class CodeReader(BaseReader):
    """Reader agent for source code artifacts."""

    supported_types = [ArtifactType.CODE]

    def __init__(self):
        super().__init__("CodeReader")

    def _get_instructions(self) -> str:
        return CODE_READER_INSTRUCTIONS

    def _get_tools(self) -> list:
        return [parse_python_code, extract_functions, analyze_data_flow]

    def _create_agent(self) -> "Agent":
        from agents import Agent
        return Agent(
            name=self.name,
            instructions=self._get_instructions(),
            tools=self._get_tools(),
        )

    async def extract_evidence(
        self,
        artifact: Artifact,
        requirements: list[EvidenceRequirement],
        relation_id: str,
    ) -> EvidenceCollection:
        """Extract evidence from source code.

        Args:
            artifact: The code artifact to read.
            requirements: Evidence requirements to satisfy.
            relation_id: The audit relation ID.

        Returns:
            Collection of extracted evidence.
        """
        collection = EvidenceCollection(relation_id=relation_id)

        # Read the source code
        source_path = Path(artifact.locator)
        if not source_path.exists():
            return collection

        source_code = source_path.read_text()
        provenance = Provenance(
            source=str(source_path),
            retrieved_by=self.name,
        )

        # Parse the code
        analysis = _parse_python_code_impl(source_code)

        if not analysis.get("success"):
            return collection

        # Extract function evidence
        for func in analysis.get("functions", []):
            evidence = self._create_evidence(
                relation_id=relation_id,
                source=str(source_path),
                evidence_type=EvidenceType.CODE_SNIPPET,
                content=f"def {func['name']}({', '.join(func['args'])})",
                provenance=provenance,
                line_number=func["lineno"],
                metadata={
                    "function_name": func["name"],
                    "args": func["args"],
                    "returns": func["returns"],
                    "docstring": func["docstring"],
                    "body_summary": func["body_summary"],
                },
            )
            collection.add(evidence)

        # Extract pattern evidence
        for pattern in analysis.get("patterns", []):
            evidence = self._create_evidence(
                relation_id=relation_id,
                source=str(source_path),
                evidence_type=EvidenceType.AST_PATTERN,
                content=f"Pattern detected: {pattern}",
                provenance=provenance,
                metadata={"pattern": pattern},
            )
            collection.add(evidence)

        # Extract issue evidence
        for issue in analysis.get("issues", []):
            evidence = self._create_evidence(
                relation_id=relation_id,
                source=str(source_path),
                evidence_type=EvidenceType.AST_PATTERN,
                content=f"Issue detected: {issue}",
                provenance=provenance,
                metadata={"issue": issue, "is_issue": True},
            )
            collection.add(evidence)

        # Extract relevant code snippets for specific evidence requirements
        for req in requirements:
            if "sorting" in req.description.lower():
                snippets = self._extract_sorting_evidence(source_code, source_path, provenance, relation_id)
                for snippet in snippets:
                    snippet.rule_ids = [req.id]
                    collection.add(snippet)

            if "weight" in req.description.lower() or "factor" in req.description.lower():
                snippets = self._extract_weight_evidence(source_code, source_path, provenance, relation_id)
                for snippet in snippets:
                    snippet.rule_ids = [req.id]
                    collection.add(snippet)

            if "affiliate" in req.description.lower() or "bias" in req.description.lower():
                snippets = self._extract_bias_evidence(source_code, source_path, provenance, relation_id)
                for snippet in snippets:
                    snippet.rule_ids = [req.id]
                    collection.add(snippet)

        return collection

    def _extract_sorting_evidence(
        self,
        source_code: str,
        source_path: Path,
        provenance: Provenance,
        relation_id: str,
    ) -> list:
        """Extract evidence related to sorting logic."""
        evidence_list = []
        lines = source_code.split("\n")

        for i, line in enumerate(lines, 1):
            if "sort" in line.lower() or "sorted" in line.lower():
                # Get context (2 lines before and after)
                start = max(0, i - 3)
                end = min(len(lines), i + 2)
                context = "\n".join(lines[start:end])

                evidence = self._create_evidence(
                    relation_id=relation_id,
                    source=str(source_path),
                    evidence_type=EvidenceType.CODE_SNIPPET,
                    content=context,
                    provenance=provenance,
                    line_number=i,
                    line_end=end,
                    metadata={"category": "sorting"},
                )
                evidence_list.append(evidence)

        return evidence_list

    def _extract_weight_evidence(
        self,
        source_code: str,
        source_path: Path,
        provenance: Provenance,
        relation_id: str,
    ) -> list:
        """Extract evidence related to weight/factor calculations."""
        evidence_list = []
        lines = source_code.split("\n")

        keywords = ["weight", "factor", "score", "rank", "priority"]

        for i, line in enumerate(lines, 1):
            line_lower = line.lower()
            if any(kw in line_lower for kw in keywords):
                # Get context
                start = max(0, i - 3)
                end = min(len(lines), i + 2)
                context = "\n".join(lines[start:end])

                evidence = self._create_evidence(
                    relation_id=relation_id,
                    source=str(source_path),
                    evidence_type=EvidenceType.CODE_SNIPPET,
                    content=context,
                    provenance=provenance,
                    line_number=i,
                    line_end=end,
                    metadata={"category": "weighting"},
                )
                evidence_list.append(evidence)

        return evidence_list

    def _extract_bias_evidence(
        self,
        source_code: str,
        source_path: Path,
        provenance: Provenance,
        relation_id: str,
    ) -> list:
        """Extract evidence related to potential bias."""
        evidence_list = []
        lines = source_code.split("\n")

        keywords = ["affiliate", "preferred", "sponsor", "promoted", "boost", "is_affiliated"]

        for i, line in enumerate(lines, 1):
            line_lower = line.lower()
            if any(kw in line_lower for kw in keywords):
                # Get context
                start = max(0, i - 3)
                end = min(len(lines), i + 2)
                context = "\n".join(lines[start:end])

                evidence = self._create_evidence(
                    relation_id=relation_id,
                    source=str(source_path),
                    evidence_type=EvidenceType.CODE_SNIPPET,
                    content=context,
                    provenance=provenance,
                    line_number=i,
                    line_end=end,
                    metadata={"category": "potential_bias", "is_issue": True},
                )
                evidence_list.append(evidence)

        return evidence_list
