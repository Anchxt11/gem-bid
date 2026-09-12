"""
Mock GSTN adapter — registration status + return filing history.

There's no public GSTN API; private aggregators (Cashfree/Karza/Signzy/
sandbox.co.in) offer sandbox verification, so this is a legitimate stand-in
until that swap happens (disclose it to judges). Keyed on `gstin`.
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

_MOCK_GSTN_DB: dict[str, dict[str, Any]] = {
    "07AABCS1234F1Z5": {
        "legal_name": "SHRESHTA ENGINEERING WORKS",
        "trade_name": "SHRESHTA ENGG",
        "registration_status": "Active",
        "taxpayer_type": "Regular",
        "last_three_returns_filed": [True, True, True],
    },
    "27AAACV5678K1Z2": {
        "legal_name": "VARUNA TECH SOLUTIONS PRIVATE LIMITED",
        "trade_name": "VARUNA TECH",
        "registration_status": "Suspended",  # -> INACTIVE
        "taxpayer_type": "Regular",
        "last_three_returns_filed": [True, False, False],
    },
    "09AACFN9012L1Z8": {
        "legal_name": "NORTHSTAR FABRICATIONS PVT LTD",  # subtle mismatch vs bidder-submitted "NORTHSTAR FABRICATORS"
        "trade_name": "NORTHSTAR",
        "registration_status": "Active",
        "taxpayer_type": "Composition",
        "last_three_returns_filed": [True, True, False],
    },
}


class MockGSTNAdapter(PortalAdapter):
    source_name = "gstn"

    def __init__(self, failure_rate: float = 0.0) -> None:
        self.failure_rate = failure_rate

    async def verify(self, bidder_input: dict[str, Any]) -> PortalVerificationResult:
        gstin = normalize(bidder_input.get("gstin"))
        submitted_name = normalize(bidder_input.get("legal_name"))

        await simulate_latency()
        try:
            maybe_fail(self.failure_rate)
        except SimulatedTimeout as exc:
            return self._unavailable(str(exc))

        record = _MOCK_GSTN_DB.get(gstin)
        if record is None:
            return self._not_found("gstin", gstin)

        retrieved_at = datetime.now(timezone.utc)
        raw_response = {"gstin": gstin, **record}

        if record["registration_status"] != "Active":
            return PortalVerificationResult(
                source=self.source_name,
                status=PortalVerificationStatus.SUCCESS,
                retrieved_fields=record,
                confidence=fields_with_confidence(0.93),
                retrieved_at=retrieved_at,
                raw_response=raw_response,
            )

        if submitted_name and submitted_name != normalize(record["legal_name"]):
            return PortalVerificationResult(
                source=self.source_name,
                status=PortalVerificationStatus.SUCCESS,
                retrieved_fields=record,
                confidence=fields_with_confidence(0.82),
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
