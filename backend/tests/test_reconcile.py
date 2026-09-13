import pytest

from backend.app.pipeline.portal_integration.base import (
    PortalVerificationResult,
    PortalVerificationStatus,
)
from backend.app.pipeline.scoring.base import MatchStatus
from backend.app.pipeline.verification.base import reconcile
from backend.app.pipeline.verification.requirement import RequirementDefinition


class FakeAlwaysMatchReconciler:
    """A stand-in Tier 3 reconciler for tests — always returns MATCH,
    instantly, no network call. Keeps the ambiguous-band test fast and
    independent of whether Ollama is actually running."""

    async def reconcile_ambiguous_name(self, bidder_name, portal_name, context):
        return MatchStatus.MATCH, "fake tier 3: forced match for test"


@pytest.mark.asyncio
async def test_reconcile_uses_overridden_bidder_name_field():
    definition = RequirementDefinition(
        portal_source="pan",
        requirement_id="pan-001",
        requirement_name="PAN Verification",
        category="pan",
        mandatory=True,
        name_field="name_on_pan",
        bidder_name_field="name_on_pan",
    )
    bidder_data = {
        "legal_name": "WRONG NAME LTD",
        "name_on_pan": "ACME PRIVATE LIMITED",
    }
    portal_result = PortalVerificationResult(
        source="pan",
        status=PortalVerificationStatus.SUCCESS,
        retrieved_fields={"name_on_pan": "ACME PRIVATE LIMITED"},
        confidence=0.95,
    )
    check = await reconcile(bidder_data, portal_result, definition)
    assert check.match_status == MatchStatus.MATCH


@pytest.mark.asyncio
async def test_reconcile_exact_match():
    definition = RequirementDefinition(
        portal_source="gstn",
        requirement_id="gstn-001",
        requirement_name="GST Registration",
        category="gstn",
        mandatory=True,
        name_field="legal_name",
        status_field="registration_status",
    )
    bidder_data = {"legal_name": "ACME LIMITED"}
    portal_result = PortalVerificationResult(
        source="gstn",
        status=PortalVerificationStatus.SUCCESS,
        retrieved_fields={"legal_name": "ACME LIMITED", "registration_status": "active"},
    )
    check = await reconcile(bidder_data, portal_result, definition)
    assert check.match_status == MatchStatus.MATCH


@pytest.mark.asyncio
async def test_reconcile_fuzzy_minor_discrepancy():
    definition = RequirementDefinition(
        portal_source="gstn",
        requirement_id="gstn-001",
        requirement_name="GST Registration",
        category="gstn",
        mandatory=True,
        name_field="legal_name",
        status_field="registration_status",
    )
    bidder_data = {"legal_name": "ACME LIMITED"}
    portal_result = PortalVerificationResult(
        source="gstn",
        status=PortalVerificationStatus.SUCCESS,
        retrieved_fields={"legal_name": "ACME LIMITED.", "registration_status": "active"},
    )
    check = await reconcile(bidder_data, portal_result, definition)
    assert check.match_status == MatchStatus.MINOR_DISCREPANCY


@pytest.mark.asyncio
async def test_reconcile_fuzzy_major_discrepancy():
    definition = RequirementDefinition(
        portal_source="gstn",
        requirement_id="gstn-001",
        requirement_name="GST Registration",
        category="gstn",
        mandatory=True,
        name_field="legal_name",
        status_field="registration_status",
    )
    bidder_data = {"legal_name": "ACME LIMITED"}
    portal_result = PortalVerificationResult(
        source="gstn",
        status=PortalVerificationStatus.SUCCESS,
        retrieved_fields={"legal_name": "COMPLETELY DIFFERENT TRADERS CO", "registration_status": "active"},
    )
    check = await reconcile(bidder_data, portal_result, definition)
    assert check.match_status == MatchStatus.MAJOR_DISCREPANCY


@pytest.mark.asyncio
async def test_reconcile_ambiguous_escalates_to_tier3():
    definition = RequirementDefinition(
        portal_source="gstn",
        requirement_id="gstn-001",
        requirement_name="GST Registration",
        category="gstn",
        mandatory=True,
        name_field="legal_name",
        status_field="registration_status",
    )
    bidder_data = {"legal_name": "ACME TRADING COMPANY"}
    portal_result = PortalVerificationResult(
        source="gstn",
        status=PortalVerificationStatus.SUCCESS,
        retrieved_fields={"legal_name": "ACME TRADE CO", "registration_status": "active"},
    )
    check = await reconcile(bidder_data, portal_result, definition, FakeAlwaysMatchReconciler())
    assert check.match_status == MatchStatus.MATCH
    assert "fake tier 3" in check.notes


@pytest.mark.asyncio
async def test_reconcile_portal_unavailable():
    definition = RequirementDefinition(
        portal_source="udyam",
        requirement_id="udyam-001",
        requirement_name="Udyam/MSME Registration",
        category="udyam",
        mandatory=True,
        name_field="enterprise_name",
        status_field="status",
    )
    bidder_data = {"legal_name": "ACME LIMITED"}
    portal_result = PortalVerificationResult(
        source="udyam",
        status=PortalVerificationStatus.UNAVAILABLE,
        raw_response={"error": "timeout"},
    )
    check = await reconcile(bidder_data, portal_result, definition)
    assert check.match_status == MatchStatus.PORTAL_UNAVAILABLE


@pytest.mark.asyncio
async def test_reconcile_not_found():
    definition = RequirementDefinition(
        portal_source="udyam",
        requirement_id="udyam-001",
        requirement_name="Udyam/MSME Registration",
        category="udyam",
        mandatory=True,
        name_field="enterprise_name",
        status_field="status",
    )
    bidder_data = {"legal_name": "ACME LIMITED"}
    portal_result = PortalVerificationResult(
        source="udyam",
        status=PortalVerificationStatus.NOT_FOUND,
    )
    check = await reconcile(bidder_data, portal_result, definition)
    assert check.match_status == MatchStatus.MAJOR_DISCREPANCY


@pytest.mark.asyncio
async def test_reconcile_listing_clean():
    definition = RequirementDefinition(
        portal_source="debarment",
        requirement_id="debarment-001",
        requirement_name="Blacklisting/Debarment Check",
        category="blacklist",
        mandatory=True,
        kind="listing",
    )
    bidder_data = {"legal_name": "ACME LIMITED"}
    portal_result = PortalVerificationResult(
        source="debarment",
        status=PortalVerificationStatus.SUCCESS,
        retrieved_fields={},
    )
    check = await reconcile(bidder_data, portal_result, definition)
    assert check.match_status == MatchStatus.MATCH


@pytest.mark.asyncio
async def test_reconcile_listing_listed():
    definition = RequirementDefinition(
        portal_source="debarment",
        requirement_id="debarment-001",
        requirement_name="Blacklisting/Debarment Check",
        category="blacklist",
        mandatory=True,
        kind="listing",
    )
    bidder_data = {"legal_name": "ACME LIMITED"}
    portal_result = PortalVerificationResult(
        source="debarment",
        status=PortalVerificationStatus.SUCCESS,
        retrieved_fields={"reason": "court order"},
    )
    check = await reconcile(bidder_data, portal_result, definition)
    assert check.match_status == MatchStatus.MAJOR_DISCREPANCY


@pytest.mark.asyncio
async def test_reconcile_status_inactive():
    definition = RequirementDefinition(
        portal_source="gstn",
        requirement_id="gstn-001",
        requirement_name="GST Registration",
        category="gstn",
        mandatory=True,
        name_field="legal_name",
        status_field="registration_status",
    )
    bidder_data = {"legal_name": "ACME LIMITED"}
    portal_result = PortalVerificationResult(
        source="gstn",
        status=PortalVerificationStatus.SUCCESS,
        retrieved_fields={"legal_name": "ACME LIMITED", "registration_status": "cancelled"},
    )
    check = await reconcile(bidder_data, portal_result, definition)
    assert check.match_status == MatchStatus.MAJOR_DISCREPANCY


@pytest.mark.asyncio
async def test_reconcile_date_expired():
    definition = RequirementDefinition(
        portal_source="nsic",
        requirement_id="nsic-001",
        requirement_name="NSIC Single Point Registration",
        category="nsic",
        mandatory=False,
        name_field="unit_name",
        date_field="validity_upto",
    )
    bidder_data = {"legal_name": "ACME LIMITED"}
    portal_result = PortalVerificationResult(
        source="nsic",
        status=PortalVerificationStatus.SUCCESS,
        retrieved_fields={"unit_name": "ACME LIMITED", "validity_upto": "2020-01-01"},
    )
    check = await reconcile(bidder_data, portal_result, definition)
    assert check.match_status == MatchStatus.MAJOR_DISCREPANCY


@pytest.mark.asyncio
async def test_reconcile_missing_name_on_one_side():
    definition = RequirementDefinition(
        portal_source="gstn",
        requirement_id="gstn-001",
        requirement_name="GST Registration",
        category="gstn",
        mandatory=True,
        name_field="legal_name",
        status_field="registration_status",
    )
    bidder_data = {}  # no legal_name at all
    portal_result = PortalVerificationResult(
        source="gstn",
        status=PortalVerificationStatus.SUCCESS,
        retrieved_fields={"legal_name": "ACME LIMITED", "registration_status": "active"},
    )
    check = await reconcile(bidder_data, portal_result, definition)
    assert check.match_status == MatchStatus.UNVERIFIABLE
