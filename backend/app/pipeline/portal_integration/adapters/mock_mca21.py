"""
Mock MCA21 adapter — company incorporation status via CIN.

No accessible sandbox. "Struck off" / "under liquidation" companies map to
INACTIVE, which is exactly the signal Layer 4's rule engine needs to hard-fail
a bidder regardless of what else checks out.
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

_MOCK_MCA21_DB: dict[str, dict[str, Any]] = {
    "U29253DL2015PTC123456": {
        "company_name": "SHRESHTA ENGINEERING WORKS PRIVATE LIMITED",
        "status": "Active",
        "incorporation_date": "2015-04-22",
        "roc": "RoC-Delhi",
    },
    "U72200MH2011PTC234567": {
        "company_name": "VARUNA TECH SOLUTIONS PRIVATE LIMITED",
        "status": "Under Liquidation",  # -> INACTIVE
        "incorporation_date": "2011-09-10",
        "roc": "RoC-Mumbai",
    },
    "U27310UP2016PTC345678": {
        "company_name": "NORTHSTAR FABRICATIONS PVT LTD",  # mismatch
        "status": "Active",
        "incorporation_date": "2016-01-05",
        "roc": "RoC-Kanpur",
    },
}


class MockMCA21Adapter(PortalAdapter):
    source_name = "mca21"

    def __init__(self, failure_rate: float = 0.0) -> None:
        self.failure_rate = failure_rate

    async def verify(self, bidder_input: dict[str, Any]) -> PortalVerificationResult:
        cin = normalize(bidder_input.get("cin"))
        submitted_name = normalize(bidder_input.get("legal_name"))

        await simulate_latency()
        try:
            maybe_fail(self.failure_rate)
        except SimulatedTimeout as exc:
            return self._unavailable(str(exc))

        record = _MOCK_MCA21_DB.get(cin)
        if record is None:
            return self._not_found("cin", cin)

        retrieved_at = datetime.now(timezone.utc)
        raw_response = {"cin": cin, **record}

        if record["status"] != "Active":
            return PortalVerificationResult(
                source=self.source_name,
                status=PortalVerificationStatus.SUCCESS,
                retrieved_fields=record,
                confidence=fields_with_confidence(0.96),
                retrieved_at=retrieved_at,
                raw_response=raw_response,
            )

        if submitted_name and submitted_name != normalize(record["company_name"]):
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
            confidence=fields_with_confidence(0.97),
            retrieved_at=retrieved_at,
            raw_response=raw_response,
        )
