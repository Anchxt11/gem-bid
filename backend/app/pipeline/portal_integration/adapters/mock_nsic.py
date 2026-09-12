"""
Mock NSIC (National Small Industries Corporation) adapter.

Single Point Registration Scheme certificates carry a validity date, so this
is the first adapter that actually exercises `PortalVerificationStatus.SUCCESS` (computed
by comparing `validity_upto` to today, not hardcoded per record). Keyed on
`nsic_registration_number`.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
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

_MOCK_NSIC_DB: dict[str, dict[str, Any]] = {
    "NSIC/SPRS/2023/001234": {
        "unit_name": "SHRESHTA ENGINEERING WORKS",
        "category": "Single Point Registration",
        "validity_upto": "2027-03-31",
    },
    "NSIC/SPRS/2020/002345": {
        "unit_name": "VARUNA TECH SOLUTIONS PRIVATE LIMITED",
        "category": "Single Point Registration",
        "validity_upto": "2024-11-30",  # in the past -> EXPIRED
    },
    "NSIC/SPRS/2022/003456": {
        "unit_name": "NORTHSTAR FABRICATORS PVT LTD",  # mismatch
        "category": "Single Point Registration",
        "validity_upto": "2026-12-31",
    },
}


class MockNSICAdapter(PortalAdapter):
    source_name = "nsic"

    def __init__(self, failure_rate: float = 0.0) -> None:
        self.failure_rate = failure_rate

    async def verify(self, bidder_input: dict[str, Any]) -> PortalVerificationResult:
        reg_number = normalize(bidder_input.get("nsic_registration_number"))
        submitted_name = normalize(bidder_input.get("legal_name"))

        await simulate_latency()
        try:
            maybe_fail(self.failure_rate)
        except SimulatedTimeout as exc:
            return self._unavailable(str(exc))

        record = _MOCK_NSIC_DB.get(reg_number)
        if record is None:
            return self._not_found("nsic_registration_number", reg_number)

        retrieved_at = datetime.now(timezone.utc)
        raw_response = {"nsic_registration_number": reg_number, **record}
        validity_upto = date.fromisoformat(record["validity_upto"])

        if validity_upto < retrieved_at.date():
            return PortalVerificationResult(
                source=self.source_name,
                status=PortalVerificationStatus.SUCCESS,
                retrieved_fields=record,
                confidence=fields_with_confidence(0.94),
                retrieved_at=retrieved_at,
                raw_response=raw_response,
            )

        if submitted_name and submitted_name != normalize(record["unit_name"]):
            return PortalVerificationResult(
                source=self.source_name,
                status=PortalVerificationStatus.SUCCESS,
                retrieved_fields=record,
                confidence=fields_with_confidence(0.84),
                retrieved_at=retrieved_at,
                raw_response=raw_response,
            )

        return PortalVerificationResult(
            source=self.source_name,
            status=PortalVerificationStatus.SUCCESS,
            retrieved_fields=record,
            confidence=fields_with_confidence(0.96),
            retrieved_at=retrieved_at,
            raw_response=raw_response,
        )
