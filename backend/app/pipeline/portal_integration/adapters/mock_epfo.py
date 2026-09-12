"""
Mock EPFO (Employees' Provident Fund) adapter.

No accessible sandbox. Keyed on `epfo_establishment_id`. A closed/exited
establishment maps to INACTIVE; a stale last-contribution date is left as a
retrieved field for Layer 3/4 to reason about rather than a hardcoded status,
since "how stale is too stale" is a scoring-rule decision, not a portal fact.
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

_MOCK_EPFO_DB: dict[str, dict[str, Any]] = {
    "DL/CPM/0012345/000": {
        "establishment_name": "SHRESHTA ENGINEERING WORKS",
        "status": "Active",
        "last_contribution_month": "2026-08",
        "employee_count": 42,
    },
    "MH/BAN/0023456/000": {
        "establishment_name": "VARUNA TECH SOLUTIONS PRIVATE LIMITED",
        "status": "Exited",  # -> INACTIVE
        "last_contribution_month": "2023-02",
        "employee_count": 0,
    },
    "UP/NOI/0034567/000": {
        "establishment_name": "NORTHSTAR FABRICATORS",
        "status": "Active",
        "last_contribution_month": "2026-07",
        "employee_count": 118,
    },
}


class MockEPFOAdapter(PortalAdapter):
    source_name = "epfo"

    def __init__(self, failure_rate: float = 0.0) -> None:
        self.failure_rate = failure_rate

    async def verify(self, bidder_input: dict[str, Any]) -> PortalVerificationResult:
        establishment_id = normalize(bidder_input.get("epfo_establishment_id"))
        submitted_name = normalize(bidder_input.get("legal_name"))

        await simulate_latency()
        try:
            maybe_fail(self.failure_rate)
        except SimulatedTimeout as exc:
            return self._unavailable(str(exc))

        record = _MOCK_EPFO_DB.get(establishment_id)
        if record is None:
            return self._not_found("epfo_establishment_id", establishment_id)

        retrieved_at = datetime.now(timezone.utc)
        raw_response = {"epfo_establishment_id": establishment_id, **record}

        if record["status"] != "Active":
            return PortalVerificationResult(
                source=self.source_name,
                status=PortalVerificationStatus.SUCCESS,
                retrieved_fields=record,
                confidence=fields_with_confidence(0.92),
                retrieved_at=retrieved_at,
                raw_response=raw_response,
            )

        if submitted_name and submitted_name != normalize(record["establishment_name"]):
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
