"""
Mock PAN + Income Tax adapter.

Like GSTN, no public govt API — aggregator sandboxes are the real substitution
later. Keyed on `pan_number`. "Inoperative" PAN (e.g. Aadhaar not linked) maps
to INACTIVE rather than a new status, keeping the enum small.
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

_MOCK_PAN_DB: dict[str, dict[str, Any]] = {
    "AABCS1234F": {
        "name_on_pan": "SHRESHTA ENGINEERING WORKS",
        "pan_status": "Valid",
        "aadhaar_linked": True,
        "last_itr_filed_ay": "2025-26",
    },
    "AAACV5678K": {
        "name_on_pan": "VARUNA TECH SOLUTIONS PRIVATE LIMITED",
        "pan_status": "Inoperative",  # -> INACTIVE
        "aadhaar_linked": False,
        "last_itr_filed_ay": "2022-23",
    },
    "AACFN9012L": {
        "name_on_pan": "NORTHSTAR FABRICATIONS PVT. LTD.",  # mismatch vs bidder-submitted name
        "pan_status": "Valid",
        "aadhaar_linked": True,
        "last_itr_filed_ay": "2025-26",
    },
}


class MockPANAdapter(PortalAdapter):
    source_name = "pan"

    def __init__(self, failure_rate: float = 0.0) -> None:
        self.failure_rate = failure_rate

    async def verify(self, bidder_input: dict[str, Any]) -> PortalVerificationResult:
        pan_number = normalize(bidder_input.get("pan_number"))
        submitted_name = normalize(bidder_input.get("legal_name"))

        await simulate_latency()
        try:
            maybe_fail(self.failure_rate)
        except SimulatedTimeout as exc:
            return self._unavailable(str(exc))

        record = _MOCK_PAN_DB.get(pan_number)
        if record is None:
            return self._not_found("pan_number", pan_number)

        retrieved_at = datetime.now(timezone.utc)
        raw_response = {"pan_number": pan_number, **record}

        if record["pan_status"] != "Valid":
            return PortalVerificationResult(
                source=self.source_name,
                status=PortalVerificationStatus.SUCCESS,
                retrieved_fields=record,
                confidence=fields_with_confidence(0.94),
                retrieved_at=retrieved_at,
                raw_response=raw_response,
            )

        if submitted_name and submitted_name != normalize(record["name_on_pan"]):
            return PortalVerificationResult(
                source=self.source_name,
                status=PortalVerificationStatus.SUCCESS,
                retrieved_fields=record,
                confidence=fields_with_confidence(0.80),
                retrieved_at=retrieved_at,
                raw_response=raw_response,
            )

        return PortalVerificationResult(
            source=self.source_name,
            status=PortalVerificationStatus.SUCCESS,
            retrieved_fields=record,
            confidence=fields_with_confidence(0.97),
            retrieved_at=retrieved_at,
            raw_response=raw_response,
        )
