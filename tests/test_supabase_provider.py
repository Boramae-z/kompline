"""Supabase Provider tests."""

import pytest
from datetime import datetime
from kompline.providers.supabase_provider import (
    SupabaseProvider,
    ComplianceItemRow,
)
from kompline.models import RuleCategory, RuleSeverity


@pytest.fixture
def provider():
    """Create a SupabaseProvider with test credentials."""
    return SupabaseProvider(
        supabase_url="https://test.supabase.co",
        supabase_key="test-key",
    )


class TestSupabaseProvider:
    """Supabase Provider unit tests."""

    def test_map_item_type_to_category(self, provider):
        """Test item type to category mapping."""
        assert provider.map_item_type_to_category("algorithm_fairness") == RuleCategory.ALGORITHM_FAIRNESS
        assert provider.map_item_type_to_category("transparency") == RuleCategory.TRANSPARENCY
        assert provider.map_item_type_to_category("data_handling") == RuleCategory.DATA_HANDLING
        assert provider.map_item_type_to_category("disclosure") == RuleCategory.DISCLOSURE
        assert provider.map_item_type_to_category("privacy") == RuleCategory.PRIVACY
        assert provider.map_item_type_to_category("security") == RuleCategory.SECURITY
        assert provider.map_item_type_to_category("unknown") == RuleCategory.ALGORITHM_FAIRNESS

    def test_map_item_type_case_insensitive(self, provider):
        """Test item type mapping is case insensitive."""
        assert provider.map_item_type_to_category("ALGORITHM_FAIRNESS") == RuleCategory.ALGORITHM_FAIRNESS
        assert provider.map_item_type_to_category("Transparency") == RuleCategory.TRANSPARENCY

    def test_map_row_to_rule(self, provider):
        """Test mapping ComplianceItemRow to Rule."""
        row = ComplianceItemRow(
            id=1,
            document_id=1,
            document_title="별지5 알고리즘공정성",
            item_index=1,
            item_type="algorithm_fairness",
            item_text="정렬 기준이 명확하게 문서화되어야 함",
            page=5,
            section="제3조",
            item_json={"severity": "high", "check_points": ["가중치 명시", "산정 방식 설명"]},
            language="ko",
            created_at=datetime.now(),
        )
        rule = provider.map_row_to_rule(row)

        assert rule.category == RuleCategory.ALGORITHM_FAIRNESS
        assert rule.severity == RuleSeverity.HIGH
        assert len(rule.check_points) == 2
        assert "가중치 명시" in rule.check_points
        assert rule.metadata["page"] == 5
        assert rule.metadata["section"] == "제3조"
        assert rule.metadata["source"] == "supabase"

    def test_map_row_to_rule_with_minimal_json(self, provider):
        """Test mapping row with minimal item_json."""
        row = ComplianceItemRow(
            id=2,
            document_id=1,
            document_title="Test Doc",
            item_index=2,
            item_type="transparency",
            item_text="- Check point 1\n- Check point 2",
            page=None,
            section=None,
            item_json=None,
            language="en",
            created_at=datetime.now(),
        )
        rule = provider.map_row_to_rule(row)

        assert rule.id == "DB-1-002"
        assert rule.category == RuleCategory.TRANSPARENCY
        assert rule.severity == RuleSeverity.HIGH  # Default
        assert len(rule.check_points) == 2

    def test_map_row_to_rule_with_custom_rule_id(self, provider):
        """Test that custom rule_id from JSON is used."""
        row = ComplianceItemRow(
            id=3,
            document_id=1,
            document_title="Test",
            item_index=3,
            item_type="privacy",
            item_text="Privacy requirement",
            page=1,
            section="1.1",
            item_json={"rule_id": "CUSTOM-001", "severity": "critical"},
            language="ko",
            created_at=datetime.now(),
        )
        rule = provider.map_row_to_rule(row)

        assert rule.id == "CUSTOM-001"
        assert rule.severity == RuleSeverity.CRITICAL

    def test_extract_check_points_from_text(self, provider):
        """Test extracting check points from text with bullets."""
        text = """
        - 가중치가 명시되어야 함
        - 산정 방식이 설명되어야 함
        * 편향이 없어야 함
        """
        points = provider._extract_check_points(text)
        assert len(points) == 3
        assert "가중치가 명시되어야 함" in points

    def test_extract_check_points_numbered(self, provider):
        """Test extracting numbered check points."""
        text = """1. First item
2. Second item
3. Third item"""
        points = provider._extract_check_points(text)
        assert len(points) == 3

    def test_extract_check_points_fallback(self, provider):
        """Test fallback to truncated text when no bullets found."""
        text = "Simple text without bullets"
        points = provider._extract_check_points(text)
        assert len(points) == 1
        assert points[0] == text

    def test_cache_behavior(self):
        """Test caching mechanism."""
        provider = SupabaseProvider(
            supabase_url="https://test.supabase.co",
            supabase_key="test-key",
            cache_ttl_seconds=300,
        )
        provider._set_cached("key", ["data"])
        assert provider._get_cached("key") == ["data"]

    def test_cache_expiry(self):
        """Test cache expiry."""
        provider = SupabaseProvider(
            supabase_url="https://test.supabase.co",
            supabase_key="test-key",
            cache_ttl_seconds=0,
        )
        provider._set_cached("key", ["data"])
        # Cache should expire immediately
        assert provider._get_cached("key") is None

    def test_cache_clear(self, provider):
        """Test cache clearing."""
        provider._set_cached("key1", ["data1"])
        provider._set_cached("key2", ["data2"])
        provider.clear_cache()
        assert provider._get_cached("key1") is None
        assert provider._get_cached("key2") is None

    def test_cache_key_generation(self, provider):
        """Test cache key generation is deterministic."""
        key1 = provider._cache_key("method", a=1, b=2)
        key2 = provider._cache_key("method", b=2, a=1)
        assert key1 == key2  # Order shouldn't matter

    def test_map_rows_to_rules(self, provider):
        """Test batch mapping of rows to rules."""
        rows = [
            ComplianceItemRow(
                id=1,
                document_id=1,
                document_title="Doc",
                item_index=1,
                item_type="algorithm_fairness",
                item_text="Rule 1",
                page=1,
                section="1",
                item_json=None,
                language="ko",
                created_at=datetime.now(),
            ),
            ComplianceItemRow(
                id=2,
                document_id=1,
                document_title="Doc",
                item_index=2,
                item_type="transparency",
                item_text="Rule 2",
                page=2,
                section="2",
                item_json=None,
                language="ko",
                created_at=datetime.now(),
            ),
        ]
        rules = provider.map_rows_to_rules(rows)
        assert len(rules) == 2
        assert rules[0].category == RuleCategory.ALGORITHM_FAIRNESS
        assert rules[1].category == RuleCategory.TRANSPARENCY

    def test_row_to_item_conversion(self, provider):
        """Test converting raw dict to ComplianceItemRow."""
        raw = {
            "id": 1,
            "document_id": 10,
            "document_title": "Test Document",
            "item_index": 5,
            "item_type": "security",
            "item_text": "Security requirement",
            "page": 3,
            "section": "2.1",
            "item_json": {"severity": "medium"},
            "language": "en",
            "created_at": datetime.now().isoformat(),
        }
        item = provider._row_to_item(raw)
        assert item.id == 1
        assert item.document_id == 10
        assert item.item_type == "security"
        assert item.item_json == {"severity": "medium"}

    def test_map_row_with_evidence_requirements(self, provider):
        """Test mapping row with evidence requirements in JSON."""
        row = ComplianceItemRow(
            id=1,
            document_id=1,
            document_title="Test",
            item_index=1,
            item_type="algorithm_fairness",
            item_text="Test rule",
            page=1,
            section="1",
            item_json={
                "severity": "high",
                "evidence_requirements": [
                    {
                        "id": "ER-001",
                        "description": "Source code review",
                        "artifact_types": ["code", "documentation"],
                        "extraction_hints": ["Look for sorting functions"],
                        "required": True,
                    }
                ],
            },
            language="ko",
            created_at=datetime.now(),
        )
        rule = provider.map_row_to_rule(row)
        assert len(rule.evidence_requirements) == 1
        assert rule.evidence_requirements[0].id == "ER-001"
        assert "code" in rule.evidence_requirements[0].artifact_types
