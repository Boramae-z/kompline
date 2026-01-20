"""PDF Reader Agent for extracting evidence from PDF documents."""

from pathlib import Path
from typing import TYPE_CHECKING, Any

try:
    from agents import function_tool
except ImportError:
    def function_tool(func):
        func.func = func
        return func

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
from kompline.tools.rag_query import query_compliance_rules

# Optional PDF extraction - pypdf is optional dependency
try:
    from pypdf import PdfReader as PyPDFReader
    HAS_PYPDF = True
except ImportError:
    HAS_PYPDF = False


PDF_READER_INSTRUCTIONS = """You are the PDF Reader Agent for Kompline.

Your role is to extract evidence from PDF documents for compliance auditing.
This includes regulatory documents, policy documents, and specifications.

## What to Extract

Based on evidence requirements, extract:
1. **Regulatory text**: Specific rules, requirements, and guidelines
2. **Tables**: Data tables with compliance criteria
3. **Definitions**: Key term definitions
4. **Cross-references**: References to other regulations or sections

## Tools Available

- `extract_pdf_text`: Extract text from PDF pages
- `search_pdf_content`: Search for specific terms in PDF
- `query_compliance_rules`: Query RAG for related compliance rules

## Output Format

For each piece of evidence, provide:
- Source document and page number
- The relevant text excerpt
- Why this is relevant to the compliance check

## Important Guidelines

- Include exact page numbers for all findings
- Quote text exactly as it appears
- Note section headers and context
- Identify both requirements AND exceptions
"""


@function_tool
def extract_pdf_text(file_path: str, page_numbers: list[int] | None = None) -> dict[str, Any]:
    """Extract text from PDF pages.

    Args:
        file_path: Path to the PDF file.
        page_numbers: Optional list of page numbers (1-indexed). If None, extract all.

    Returns:
        Dictionary with extracted text per page.
    """
    if not HAS_PYPDF:
        return {"success": False, "error": "pypdf not installed. Install with: pip install pypdf"}

    try:
        reader = PyPDFReader(file_path)
        result = {"success": True, "pages": {}, "total_pages": len(reader.pages)}

        pages_to_extract = page_numbers if page_numbers else range(1, len(reader.pages) + 1)

        for page_num in pages_to_extract:
            if 1 <= page_num <= len(reader.pages):
                page = reader.pages[page_num - 1]
                text = page.extract_text()
                result["pages"][page_num] = text

        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


@function_tool
def search_pdf_content(file_path: str, search_term: str) -> dict[str, Any]:
    """Search for a term in PDF content.

    Args:
        file_path: Path to the PDF file.
        search_term: Term to search for.

    Returns:
        Dictionary with matches and their locations.
    """
    if not HAS_PYPDF:
        return {"success": False, "error": "pypdf not installed"}

    try:
        reader = PyPDFReader(file_path)
        matches = []

        for page_num, page in enumerate(reader.pages, 1):
            text = page.extract_text()
            if search_term.lower() in text.lower():
                # Find context around the match
                lines = text.split("\n")
                for i, line in enumerate(lines):
                    if search_term.lower() in line.lower():
                        # Get surrounding context
                        start = max(0, i - 1)
                        end = min(len(lines), i + 2)
                        context = "\n".join(lines[start:end])
                        matches.append({
                            "page": page_num,
                            "context": context,
                            "line": line.strip(),
                        })

        return {"success": True, "search_term": search_term, "matches": matches}
    except Exception as e:
        return {"success": False, "error": str(e)}


class PDFReader(BaseReader):
    """Reader agent for PDF document artifacts."""

    supported_types = [ArtifactType.PDF, ArtifactType.DOCUMENT]

    def __init__(self):
        super().__init__("PDFReader")

    def _get_instructions(self) -> str:
        return PDF_READER_INSTRUCTIONS

    def _get_tools(self) -> list:
        return [extract_pdf_text, search_pdf_content, query_compliance_rules]

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
        """Extract evidence from PDF document.

        Args:
            artifact: The PDF artifact to read.
            requirements: Evidence requirements to satisfy.
            relation_id: The audit relation ID.

        Returns:
            Collection of extracted evidence.
        """
        collection = EvidenceCollection(relation_id=relation_id)

        if not HAS_PYPDF:
            # Return empty collection if pypdf not available
            return collection

        source_path = Path(artifact.locator)
        if not source_path.exists():
            return collection

        provenance = Provenance(
            source=str(source_path),
            retrieved_by=self.name,
        )

        # Extract all text first
        extraction = extract_pdf_text.func(str(source_path))

        if not extraction.get("success"):
            return collection

        # Create evidence for each page
        for page_num, text in extraction.get("pages", {}).items():
            if text.strip():
                evidence = self._create_evidence(
                    relation_id=relation_id,
                    source=str(source_path),
                    evidence_type=EvidenceType.DOCUMENT_EXCERPT,
                    content=text[:2000],  # Limit content size
                    provenance=provenance,
                    page_number=page_num,
                    metadata={"full_length": len(text)},
                )
                collection.add(evidence)

        # Search for requirement-specific content
        for req in requirements:
            # Extract keywords from requirement
            keywords = self._extract_keywords(req.description)
            for keyword in keywords:
                search_result = search_pdf_content.func(str(source_path), keyword)
                if search_result.get("success"):
                    for match in search_result.get("matches", []):
                        evidence = self._create_evidence(
                            relation_id=relation_id,
                            source=str(source_path),
                            evidence_type=EvidenceType.DOCUMENT_EXCERPT,
                            content=match["context"],
                            provenance=provenance,
                            page_number=match["page"],
                            metadata={"search_term": keyword},
                        )
                        evidence.rule_ids = [req.id]
                        collection.add(evidence)

        return collection

    def _extract_keywords(self, description: str) -> list[str]:
        """Extract search keywords from a requirement description."""
        # Simple keyword extraction - can be enhanced
        keywords = []
        important_terms = [
            "sorting", "ranking", "weight", "factor", "algorithm",
            "disclosure", "transparency", "fairness", "bias",
            "affiliate", "priority", "preference",
        ]

        desc_lower = description.lower()
        for term in important_terms:
            if term in desc_lower:
                keywords.append(term)

        return keywords[:5]  # Limit to top 5 keywords
