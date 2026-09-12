"""
Mock ESIC (Employees' State Insurance) adapter.

No accessible sandbox. Keyed on `esic_code`. Mirrors the EPFO adapter's shape
closely since both are labour-compliance registrations with the same kinds
of real-world edge cases (closed employer, name drift over the years).
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

_MOCK_ESIC_DB: dict[str, dict[str, Any]] = {
    "11000012340000999": {
        "employer_name": "SHRESHTA ENGINEERING WORKS",
        "status": "Active",
        "coverage_type": "Principal Employer",
    },
    "27000023450000888": {
        "employer_name": "VARUNA TECH SOLUTIONS PRIVATE LIMITED",
        "status": "Closed",  # -> INACTIVE
        "coverage_type": "Principal Employer",
    },
    "09000034560000777": {
        "employer_name": "NORTHSTAR FABRICATORS PVT LTD",  # mismatch
        "status": "Active",
        "coverage_type": "Immediate Employer",
    },
}


class MockESICAdapter(PortalAdapter):
    source_name = "esic"

    def __init__(self, failure_rate: float = 0.0) -> None:
        self.failure_rate = failure_rate

    async def verify(self, bidder_input: dict[str, Any]) -> PortalVerificationResult:
        esic_code = normalize(bidder_input.get("esic_code"))
        submitted_name = normalize(bidder_input.get("legal_name"))

        await simulate_latency()
        try:
            maybe_fail(self.failure_rate)
        except SimulatedTimeout as exc:
            return self._unavailable(str(exc))

        record = _MOCK_ESIC_DB.get(esic_code)
        if record is None:
            return self._not_found("esic_code", esic_code)

        retrieved_at = datetime.now(timezone.utc)
        raw_response = {"esic_code": esic_code, **record}

        if record["status"] != "Active":
            return PortalVerificationResult(
                source=self.source_name,
                status=PortalVerificationStatus.SUCCESS,
                retrieved_fields=record,
                confidence=fields_with_confidence(0.91),
                retrieved_at=retrieved_at,
                raw_response=raw_response,
            )

        if submitted_name and submitted_name != normalize(record["employer_name"]):
            return PortalVerificationResult(
                source=self.source_name,
                status=PortalVerificationStatus.SUCCESS,
                retrieved_fields=record,
                confidence=fields_with_confidence(0.81),
                retrieved_at=retrieved_at,
                raw_response=raw_response,
            )

        return PortalVerificationResult(
            source=self.source_name,
            status=PortalVerificationStatus.SUCCESS,
            retrieved_fields=record,
            confidence=fields_with_confidence(0.95),
            retrieved_at=retrieved_at,
            raw_response=raw_response,
        )
