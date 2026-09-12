"""
Mock Startup India / DPIIT recognition adapter.

DPIIT recognition certificates are valid for a fixed period from issue, so
this also computes EXPIRED from a date rather than a hardcoded field. Keyed
on `dpiit_recognition_number`.
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

_MOCK_STARTUP_INDIA_DB: dict[str, dict[str, Any]] = {
    "DIPP123456": {
        "entity_name": "SHRESHTA ENGINEERING WORKS PRIVATE LIMITED",
        "sector": "Manufacturing",
        "recognition_date": "2023-05-01",
        "valid_upto": "2033-05-01",
    },
    "DIPP234567": {
        "entity_name": "VARUNA TECH SOLUTIONS PRIVATE LIMITED",
        "sector": "IT Services",
        "recognition_date": "2016-04-01",
        "valid_upto": "2026-04-01",  # borderline / may already be past -> EXPIRED
    },
    "DIPP345678": {
        "entity_name": "NORTHSTAR FABRICATIONS PVT LTD",  # mismatch
        "sector": "Manufacturing",
        "recognition_date": "2022-08-15",
        "valid_upto": "2032-08-15",
    },
}


class MockStartupIndiaAdapter(PortalAdapter):
    source_name = "startup_india"

    def __init__(self, failure_rate: float = 0.0) -> None:
        self.failure_rate = failure_rate

    async def verify(self, bidder_input: dict[str, Any]) -> PortalVerificationResult:
        recognition_number = normalize(bidder_input.get("dpiit_recognition_number"))
        submitted_name = normalize(bidder_input.get("legal_name"))

        await simulate_latency()
        try:
            maybe_fail(self.failure_rate)
        except SimulatedTimeout as exc:
            return self._unavailable(str(exc))

        record = _MOCK_STARTUP_INDIA_DB.get(recognition_number)
        if record is None:
            return self._not_found("dpiit_recognition_number", recognition_number)

        retrieved_at = datetime.now(timezone.utc)
        raw_response = {"dpiit_recognition_number": recognition_number, **record}
        valid_upto = date.fromisoformat(record["valid_upto"])

        if valid_upto < retrieved_at.date():
            return PortalVerificationResult(
                source=self.source_name,
                status=PortalVerificationStatus.SUCCESS,
                retrieved_fields=record,
                confidence=fields_with_confidence(0.93),
                retrieved_at=retrieved_at,
                raw_response=raw_response,
            )

        if submitted_name and submitted_name != normalize(record["entity_name"]):
            return PortalVerificationResult(
                source=self.source_name,
                status=PortalVerificationStatus.SUCCESS,
                retrieved_fields=record,
                confidence=fields_with_confidence(0.83),
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
