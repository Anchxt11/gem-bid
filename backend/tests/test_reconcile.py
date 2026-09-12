import pytest

from backend.app.pipeline.portal_integration.base import (
    PortalVerificationResult,
    PortalVerificationStatus,
)
from backend.app.pipeline.scoring.base import MatchStatus
from backend.app.pipeline.verification.base import reconcile
from backend.app.pipeline.verification.requirement import RequirementDefinition


@pytest.mark.asyncio
async def test_reconcile_uses_overridden_bidder_name_field():
    # A fake portal definition where the bidder-side name comes from
    # "name_on_pan" instead of the default "legal_name".
    definition = RequirementDefinition(
        portal_source="pan",
        requirement_id="pan-001",
        requirement_name="PAN Verification",
        category="pan",
        mandatory=True,
        name_field="name_on_pan",
        bidder_name_field="name_on_pan",
    )

    # Bidder data has BOTH keys, with DIFFERENT values on purpose.
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

    # If it's reading name_on_pan (correct), this is a MATCH.
    # If it's still reading legal_name (the bug), this would be a discrepancy.
    assert check.match_status == MatchStatus.MATCH