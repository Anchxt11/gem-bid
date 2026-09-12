"""
Mock blacklisting/debarment adapter.

Structurally different from the others: this isn't "does a registration
exist and match", it's "does this bidder appear on a debarment list at all".
No new PortalVerificationStatus values are introduced to keep Layer 3/4 branching simple:

- Bidder NOT on any list  -> VERIFIED   (clean; retrieved_fields empty)
- Bidder found on a list  -> MISMATCH   (retrieved_fields carries the debarment record —
                                          Layer 4's rule engine should treat this as an
                                          automatic hard-fail regardless of other scores)

Keyed on `pan_number` (debarment lists are typically cross-referenced by PAN/CIN,
not by a portal-specific ID, since the whole point is catching bidders trying to
re-enter under a new company name).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from backend.app.pipeline.portal_integration.adapters._common import (
    SimulatedTimeout,
    fields_with_confidence,
    maybe_fail,
    normalize,
    simulate_latency,
)
from backend.app.pipeline.portal_integration.base import (
    PortalAdapter,
    PortalVerificationStatus,
    PortalVerificationResult,
)

_MOCK_DEBARMENT_DB: dict[str, dict[str, Any]] = {
    "AAACV5678K": {
        "entity_name": "VARUNA TECH SOLUTIONS PRIVATE LIMITED",
        "debarring_authority": "Ministry of Electronics & IT",
        "reason": "Submission of falsified test certificates",
        "debarment_start": "2025-01-10",
        "debarment_end": "2027-01-09",
    },
}


class MockDebarmentAdapter(PortalAdapter):
    source_name = "debarment"

    def __init__(self, failure_rate: float = 0.0) -> None:
        self.failure_rate = failure_rate

    async def verify(self, bidder_input: dict[str, Any]) -> PortalVerificationResult:
        pan_number = normalize(bidder_input.get("pan_number"))

        await simulate_latency()
        try:
            maybe_fail(self.failure_rate)
        except SimulatedTimeout as exc:
            return self._unavailable(str(exc))

        retrieved_at = datetime.now(timezone.utc)
        record = _MOCK_DEBARMENT_DB.get(pan_number)

        if record is None:
            return PortalVerificationResult(
                source=self.source_name,
                status=PortalVerificationStatus.SUCCESS,
                retrieved_fields={},
                confidence=fields_with_confidence(0.99),
                retrieved_at=retrieved_at,
                raw_response={"pan_number": pan_number, "listed": False},
            )

        return PortalVerificationResult(
            source=self.source_name,
            status=PortalVerificationStatus.SUCCESS,
            retrieved_fields=record,
            confidence=fields_with_confidence(0.99),
            retrieved_at=retrieved_at,
            raw_response={"pan_number": pan_number, "listed": True, **record},
        )
