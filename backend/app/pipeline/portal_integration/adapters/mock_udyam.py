"""
Mock Udyam/MSME registration adapter.

No accessible sandbox exists for Udyam, so this simulates realistic responses
shaped like the real Udyam Registration Certificate schema. Keyed on
`udyam_number` (format: UDYAM-XX-00-0000000).

This is the reference implementation — the pattern proven here (dataset dict +
lookup + edge-case branching + latency/failure simulation) is copied
mechanically by every other mock adapter in this package.
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

# Realistic mock "Udyam database" — one row per edge case we need Layer 3/4 to handle.
_MOCK_UDYAM_DB: dict[str, dict[str, Any]] = {
    "UDYAM-DL-03-1234567": {
        "enterprise_name": "SHRESHTA ENGINEERING WORKS",
        "category": "Small",
        "major_activity": "Manufacturing",
        "registration_date": "2021-06-14",
        "status": "Active",
    },
    "UDYAM-MH-05-2345678": {
        "enterprise_name": "VARUNA TECH SOLUTIONS PRIVATE LIMITED",
        "category": "Micro",
        "major_activity": "Services",
        "registration_date": "2019-11-02",
        "status": "Cancelled",  # -> INACTIVE
    },
    "UDYAM-UP-11-3456789": {
        "enterprise_name": "NORTHSTAR FABRICATORS",  # deliberately different from bidder's submitted name -> MISMATCH
        "category": "Medium",
        "major_activity": "Manufacturing",
        "registration_date": "2020-01-30",
        "status": "Active",
    },
}


class MockUdyamAdapter(PortalAdapter):
    source_name = "udyam"

    def __init__(self, failure_rate: float = 0.0) -> None:
        self.failure_rate = failure_rate

    async def verify(self, bidder_input: dict[str, Any]) -> PortalVerificationResult:
        udyam_number = normalize(bidder_input.get("udyam_number"))
        submitted_name = normalize(bidder_input.get("legal_name"))

        await simulate_latency()
        try:
            maybe_fail(self.failure_rate)
        except SimulatedTimeout as exc:
            return self._unavailable(str(exc))

        record = _MOCK_UDYAM_DB.get(udyam_number)
        if record is None:
            return self._not_found("udyam_number", udyam_number)

        retrieved_at = datetime.now(timezone.utc)
        raw_response = {"udyam_number": udyam_number, **record}

        if record["status"] != "Active":
            return PortalVerificationResult(
                source=self.source_name,
                status=PortalVerificationStatus.SUCCESS,
                retrieved_fields=record,
                confidence=fields_with_confidence(0.95),
                retrieved_at=retrieved_at,
                raw_response=raw_response,
            )

        if submitted_name and submitted_name != normalize(record["enterprise_name"]):
            return PortalVerificationResult(
                source=self.source_name,
                status=PortalVerificationStatus.SUCCESS,
                retrieved_fields=record,
                confidence=fields_with_confidence(0.85),
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

_MOCK_UDYAM_DB["UDYAM-DL-99-8888888"] = {"enterprise_name": "INNOVATE TECH A.I. SOLUTIONS", "category": "Small", "status": "Active"}

_MOCK_UDYAM_DB["UDYAM-KA-07-5550001"] = {'enterprise_name': 'BHARAT DEFENCE SYSTEMS PVT LTD', 'category': 'Medium', 'major_activity': 'Manufacturing', 'registration_date': '2020-03-15', 'status': 'Active'}

_MOCK_UDYAM_DB["UDYAM-MH-02-7770001"] = {'enterprise_name': 'TATA ADVANCED SYSTEMS LIMITED', 'category': 'Medium', 'major_activity': 'Manufacturing', 'registration_date': '2019-07-20', 'status': 'Active'}
