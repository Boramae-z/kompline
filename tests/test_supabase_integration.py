"""Supabase integration test (requires DB connection)."""

import os
import pytest
from kompline.registry import get_compliance_registry


# Skip integration tests if credentials are not set
requires_supabase = pytest.mark.skipif(
    not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_SERVICE_ROLE_KEY"),
    reason="Supabase credentials not set (SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY required)"
)


@pytest.mark.asyncio
@pytest.mark.integration
@requires_supabase
async def test_full_supabase_flow():
    """Test loading from Supabase and using for evaluation.

    This test requires a running Supabase/Postgres database with
    compliance_items table populated.

    Run with: pytest tests/test_supabase_integration.py -v -m integration
    """
    registry = get_compliance_registry()

    # Load from database
    compliance = await registry.load_from_supabase(
        language="ko",
        compliance_id="byeolji5-db",
    )

    assert compliance is not None
    assert len(compliance.rules) > 0

    # Verify rules have expected structure
    for rule in compliance.rules:
        assert rule.id is not None
        assert rule.category is not None
        assert rule.metadata.get("source") == "supabase"


@pytest.mark.asyncio
@pytest.mark.integration
@requires_supabase
async def test_load_by_document_id():
    """Test loading compliance items by document ID."""
    registry = get_compliance_registry()

    # Load specific document (adjust document_id as needed)
    compliance = await registry.load_from_supabase(
        document_id=1,
        compliance_id="doc-1-compliance",
    )

    assert compliance is not None
    assert compliance.metadata["document_id"] == 1


@pytest.mark.asyncio
@pytest.mark.integration
@requires_supabase
async def test_load_by_item_type():
    """Test loading compliance items by item type."""
    registry = get_compliance_registry()

    compliance = await registry.load_from_supabase(
        item_type="algorithm_fairness",
        compliance_id="fairness-compliance",
    )

    assert compliance is not None
    # All rules should be algorithm_fairness category
    for rule in compliance.rules:
        assert rule.category.value == "algorithm_fairness"


@pytest.mark.integration
@requires_supabase
def test_sync_loading():
    """Test synchronous loading wrapper."""
    registry = get_compliance_registry()

    compliance = registry.load_from_supabase_sync(
        language="ko",
        compliance_id="sync-test-compliance",
    )

    assert compliance is not None
    assert len(compliance.rules) > 0
