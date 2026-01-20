"""ComplianceRegistry Supabase integration tests."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime
from kompline.registry.compliance_registry import ComplianceRegistry
from kompline.providers.supabase_provider import ComplianceItemRow
from kompline.models import RuleCategory, RuleSeverity, Rule


@pytest.fixture
def mock_items():
    """Sample compliance items for testing."""
    return [
        ComplianceItemRow(
            id=1,
            document_id=1,
            document_title="알고리즘 공정성 자가평가",
            item_index=1,
            item_type="algorithm_fairness",
            item_text="정렬 기준 투명성",
            page=1,
            section="1조",
            item_json={"severity": "high"},
            language="ko",
            created_at=datetime.now(),
        ),
        ComplianceItemRow(
            id=2,
            document_id=1,
            document_title="알고리즘 공정성 자가평가",
            item_index=2,
            item_type="algorithm_fairness",
            item_text="계열사 편향 금지",
            page=2,
            section="2조",
            item_json={"severity": "critical"},
            language="ko",
            created_at=datetime.now(),
        ),
    ]


@pytest.fixture
def mock_rules():
    """Sample rules for testing."""
    return [
        Rule(
            id="DB-1-001",
            title="알고리즘 공정성 자가평가 - Item 1",
            description="정렬 기준 투명성",
            category=RuleCategory.ALGORITHM_FAIRNESS,
            severity=RuleSeverity.HIGH,
            check_points=["정렬 기준 투명성"],
            pass_criteria="",
            fail_examples=[],
            evidence_requirements=[],
            metadata={"source": "supabase", "source_document_id": 1},
        ),
        Rule(
            id="DB-1-002",
            title="알고리즘 공정성 자가평가 - Item 2",
            description="계열사 편향 금지",
            category=RuleCategory.ALGORITHM_FAIRNESS,
            severity=RuleSeverity.CRITICAL,
            check_points=["계열사 편향 금지"],
            pass_criteria="",
            fail_examples=[],
            evidence_requirements=[],
            metadata={"source": "supabase", "source_document_id": 1},
        ),
    ]


class TestComplianceRegistrySupabase:
    """Tests for ComplianceRegistry Supabase loading."""

    @pytest.mark.asyncio
    async def test_load_from_supabase_by_document(self, mock_items, mock_rules):
        """Test loading compliance from Supabase by document ID."""
        registry = ComplianceRegistry()

        with patch("kompline.providers.supabase_provider.SupabaseProvider") as MockProvider:
            mock_provider = MockProvider.return_value
            mock_provider.fetch_items_by_document = AsyncMock(return_value=mock_items)
            mock_provider.map_rows_to_rules = MagicMock(return_value=mock_rules)

            compliance = await registry.load_from_supabase(
                document_id=1,
                language="ko",
                compliance_id="test-compliance",
            )

            assert compliance.id == "test-compliance"
            assert len(compliance.rules) == 2
            assert compliance.metadata["source"] == "supabase"
            mock_provider.fetch_items_by_document.assert_called_once_with(1, "ko")

    @pytest.mark.asyncio
    async def test_load_from_supabase_by_type(self, mock_items, mock_rules):
        """Test loading compliance from Supabase by item type."""
        registry = ComplianceRegistry()

        with patch("kompline.providers.supabase_provider.SupabaseProvider") as MockProvider:
            mock_provider = MockProvider.return_value
            mock_provider.fetch_items_by_type = AsyncMock(return_value=mock_items)
            mock_provider.map_rows_to_rules = MagicMock(return_value=mock_rules)

            compliance = await registry.load_from_supabase(
                item_type="algorithm_fairness",
                compliance_id="fairness-compliance",
            )

            assert compliance.id == "fairness-compliance"
            mock_provider.fetch_items_by_type.assert_called_once_with("algorithm_fairness", None)

    @pytest.mark.asyncio
    async def test_load_from_supabase_all(self, mock_items, mock_rules):
        """Test loading all compliance items from Supabase."""
        registry = ComplianceRegistry()

        with patch("kompline.providers.supabase_provider.SupabaseProvider") as MockProvider:
            mock_provider = MockProvider.return_value
            mock_provider.fetch_all_items = AsyncMock(return_value=mock_items)
            mock_provider.map_rows_to_rules = MagicMock(return_value=mock_rules)

            compliance = await registry.load_from_supabase(
                language="ko",
            )

            assert compliance is not None
            mock_provider.fetch_all_items.assert_called_once_with("ko")

    @pytest.mark.asyncio
    async def test_load_from_supabase_empty_raises(self):
        """Test that loading empty results raises ValueError."""
        registry = ComplianceRegistry()

        with patch("kompline.providers.supabase_provider.SupabaseProvider") as MockProvider:
            mock_provider = MockProvider.return_value
            mock_provider.fetch_all_items = AsyncMock(return_value=[])

            with pytest.raises(ValueError, match="No compliance items found"):
                await registry.load_from_supabase()

    @pytest.mark.asyncio
    async def test_load_from_supabase_registers_compliance(self, mock_items, mock_rules):
        """Test that loaded compliance is registered in the registry."""
        registry = ComplianceRegistry()

        with patch("kompline.providers.supabase_provider.SupabaseProvider") as MockProvider:
            mock_provider = MockProvider.return_value
            mock_provider.fetch_items_by_document = AsyncMock(return_value=mock_items)
            mock_provider.map_rows_to_rules = MagicMock(return_value=mock_rules)

            compliance = await registry.load_from_supabase(
                document_id=1,
                compliance_id="registered-compliance",
            )

            # Should be registered
            retrieved = registry.get("registered-compliance")
            assert retrieved is not None
            assert retrieved.id == compliance.id

    @pytest.mark.asyncio
    async def test_load_from_supabase_updates_existing(self, mock_items, mock_rules):
        """Test that loading with same ID updates existing compliance."""
        registry = ComplianceRegistry()

        with patch("kompline.providers.supabase_provider.SupabaseProvider") as MockProvider:
            mock_provider = MockProvider.return_value
            mock_provider.fetch_items_by_document = AsyncMock(return_value=mock_items)
            mock_provider.map_rows_to_rules = MagicMock(return_value=mock_rules)

            # Load first time
            await registry.load_from_supabase(
                document_id=1,
                compliance_id="update-test",
            )

            # Load second time with same ID - should update, not raise
            compliance2 = await registry.load_from_supabase(
                document_id=1,
                compliance_id="update-test",
            )

            assert registry.get("update-test") is not None
            assert len(registry) == 1  # Only one compliance

    @pytest.mark.asyncio
    async def test_load_from_supabase_metadata(self, mock_items, mock_rules):
        """Test that metadata is correctly set."""
        registry = ComplianceRegistry()

        with patch("kompline.providers.supabase_provider.SupabaseProvider") as MockProvider:
            mock_provider = MockProvider.return_value
            mock_provider.fetch_items_by_document = AsyncMock(return_value=mock_items)
            mock_provider.map_rows_to_rules = MagicMock(return_value=mock_rules)

            compliance = await registry.load_from_supabase(
                document_id=1,
                compliance_id="metadata-test",
            )

            assert compliance.metadata["source"] == "supabase"
            assert compliance.metadata["document_id"] == 1
            assert "loaded_at" in compliance.metadata
            assert compliance.metadata["item_count"] == 2

    def test_load_from_supabase_sync(self, mock_items, mock_rules):
        """Test synchronous wrapper for load_from_supabase."""
        registry = ComplianceRegistry()

        with patch("kompline.providers.supabase_provider.SupabaseProvider") as MockProvider:
            mock_provider = MockProvider.return_value
            mock_provider.fetch_items_by_document = AsyncMock(return_value=mock_items)
            mock_provider.map_rows_to_rules = MagicMock(return_value=mock_rules)

            compliance = registry.load_from_supabase_sync(
                document_id=1,
                compliance_id="sync-test",
            )

            assert compliance.id == "sync-test"
            assert len(compliance.rules) == 2
