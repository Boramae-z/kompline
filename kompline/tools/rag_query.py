"""RAG query tools for compliance rule matching."""

from dataclasses import dataclass
from typing import Any

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    httpx = None  # type: ignore
    HAS_HTTPX = False

try:
    from agents import function_tool
except ImportError:
    def function_tool(func=None, **kwargs):
        """Fallback decorator when agents SDK not installed."""
        def decorator(f):
            f.func = f
            return f
        if func is not None:
            return decorator(func)
        return decorator

try:
    from config.settings import settings
except ImportError:
    # Fallback for when running as a module
    class _Settings:
        rag_api_url = "http://localhost:8000"
    settings = _Settings()


@dataclass
class RAGCitation:
    """Citation from RAG query results.

    Provides traceable reference to the source document.
    """

    source: str  # Document/regulation name
    text: str  # Relevant excerpt
    relevance: float  # Similarity score
    page: int | None = None
    section: str | None = None
    chunk_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "source": self.source,
            "text": self.text,
            "relevance": self.relevance,
            "page": self.page,
            "section": self.section,
            "chunk_id": self.chunk_id,
        }


@dataclass
class ComplianceRule:
    """A compliance rule from the knowledge base."""

    rule_id: str
    title: str
    description: str
    category: str
    check_points: list[str]
    pass_criteria: str
    fail_examples: list[str]
    relevance_score: float


@function_tool
async def query_compliance_rules(
    query: str,
    category: str | None = None,
    top_k: int = 5,
) -> dict[str, Any]:
    """Query the compliance rules knowledge base using RAG.

    Args:
        query: The search query describing the code pattern or compliance concern.
        category: Optional category filter (e.g., "algorithm_fairness", "data_handling").
        top_k: Number of top results to return.

    Returns:
        Dictionary containing matched rules and relevance scores.
    """
    if not HAS_HTTPX:
        return {
            "success": False,
            "error": "httpx not installed. Install with: pip install httpx",
            "query": query,
            "rules": [],
        }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.rag_api_url}/query",
                json={
                    "query": query,
                    "top_k": top_k,
                },
                timeout=30.0,
            )
            response.raise_for_status()
            results = response.json()

            rules = []
            citations = []
            for item in results.get("results", []):
                rule = {
                    "rule_id": item.get("chunk_id", "unknown"),
                    "content": item.get("text", ""),
                    "relevance_score": item.get("score", 0.0),
                    "source": item.get("document", ""),
                    "page": item.get("page", 0),
                }
                if category is None or category.lower() in rule["content"].lower():
                    rules.append(rule)

                    # Create citation for traceability
                    citation = RAGCitation(
                        source=item.get("document", "Unknown"),
                        text=item.get("text", "")[:200],  # Truncate for display
                        relevance=item.get("score", 0.0),
                        page=item.get("page"),
                        section=item.get("section"),
                        chunk_id=item.get("chunk_id"),
                    )
                    citations.append(citation.to_dict())

            return {
                "success": True,
                "query": query,
                "rules": rules[:top_k],
                "citations": citations[:top_k],
                "total_found": len(rules),
            }

    except httpx.HTTPError as e:
        return {
            "success": False,
            "error": f"RAG API error: {str(e)}",
            "query": query,
            "rules": [],
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}",
            "query": query,
            "rules": [],
        }


# Fallback rules for when RAG is unavailable
BUILTIN_RULES = [
    {
        "rule_id": "ALG-001",
        "title": "Algorithm Fairness - Sorting Transparency",
        "description": "Sorting algorithms must have clear, documented criteria",
        "category": "algorithm_fairness",
        "check_points": [
            "Sorting criteria must be explicitly defined",
            "Weight factors must be documented",
            "No hidden prioritization allowed",
        ],
        "pass_criteria": "All sorting factors are documented and justified",
        "fail_examples": ["Undocumented weight factors", "Hidden sponsor prioritization"],
        "citation": {
            "source": "별지5 제2조 제1항",
            "text": "정렬 알고리즘은 명확하고 문서화된 기준을 가져야 합니다",
            "relevance": 1.0,
            "section": "알고리즘 공정성",
        },
    },
    {
        "rule_id": "ALG-002",
        "title": "Algorithm Fairness - No Discriminatory Ranking",
        "description": "Rankings must not discriminate based on business relationships",
        "category": "algorithm_fairness",
        "check_points": [
            "No preferential treatment for affiliated products",
            "Equal opportunity for all eligible products",
            "Ranking factors must be consumer-relevant",
        ],
        "pass_criteria": "Ranking based solely on objective, consumer-relevant factors",
        "fail_examples": ["Affiliated products ranked higher", "Paid placement without disclosure"],
        "citation": {
            "source": "별지5 제3조 제2항",
            "text": "계열사 상품에 대한 부당한 우대 금지",
            "relevance": 1.0,
            "section": "계열사 편향 금지",
        },
    },
    {
        "rule_id": "ALG-003",
        "title": "Algorithm Fairness - Randomization Disclosure",
        "description": "Any randomization in results must be disclosed",
        "category": "algorithm_fairness",
        "check_points": [
            "Randomization must be disclosed to users",
            "Random seed must be documented",
            "Randomization should not disadvantage any party",
        ],
        "pass_criteria": "Randomization is disclosed and does not create unfair advantages",
        "fail_examples": ["Hidden shuffle without disclosure", "Biased random selection"],
        "citation": {
            "source": "별지5 제4조",
            "text": "결과에 영향을 미치는 무작위화는 공개해야 합니다",
            "relevance": 1.0,
            "section": "무작위화 공개",
        },
    },
]


# Builtin citations for traceability
BUILTIN_CITATIONS = [
    {
        "source": "별지5 제2조 제1항",
        "text": "정렬 알고리즘은 명확하고 문서화된 기준을 가져야 합니다",
        "relevance": 1.0,
        "section": "알고리즘 공정성",
    },
    {
        "source": "별지5 제3조 제2항",
        "text": "계열사 상품에 대한 부당한 우대 금지",
        "relevance": 1.0,
        "section": "계열사 편향 금지",
    },
    {
        "source": "별지5 제4조",
        "text": "결과에 영향을 미치는 무작위화는 공개해야 합니다",
        "relevance": 1.0,
        "section": "무작위화 공개",
    },
]


@function_tool(strict_mode=False)
def get_builtin_rules(category: str | None = None) -> dict[str, Any]:
    """Get built-in compliance rules when RAG is unavailable.

    Args:
        category: Optional category filter.

    Returns:
        Dictionary containing rules and their citations.
    """
    if category:
        filtered_rules = [r for r in BUILTIN_RULES if r["category"] == category]
    else:
        filtered_rules = BUILTIN_RULES

    # Extract citations from rules
    citations = [r.get("citation") for r in filtered_rules if r.get("citation")]

    return {
        "success": True,
        "rules": filtered_rules,
        "citations": citations,
        "total_found": len(filtered_rules),
    }


def get_citation_for_rule(rule_id: str) -> dict[str, Any] | None:
    """Get citation for a specific rule.

    Args:
        rule_id: The rule ID to get citation for.

    Returns:
        Citation dictionary or None if not found.
    """
    for rule in BUILTIN_RULES:
        if rule["rule_id"] == rule_id:
            return rule.get("citation")
    return None
