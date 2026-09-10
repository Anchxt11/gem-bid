import asyncio
import random

from backend.app.pipeline.portal_integration.base import (
    PortalAdapter,
    PortalVerificationResult,
    PortalVerificationStatus,
)


class MockUdyamAdapter(PortalAdapter):
    """
    Stands in for the real Udyam portal (no public API/sandbox exists).
    Returns realistic mock data shaped like the real Udyam certificate
    response, including deliberate edge cases so the reconciliation
    layer (Layer 3) has something real to chew on later.
    """

    source_name = "udyam"

    async def verify(self, bidder_data: dict) -> PortalVerificationResult:
        udyam_number = bidder_data.get("udyam_number")

        # simulate real network latency so asyncio.gather concurrency
        # is actually meaningful to demo later, not instant no-ops
        await asyncio.sleep(random.uniform(0.3, 0.8))

        if not udyam_number:
            return PortalVerificationResult(
                source=self.source_name,
                status=PortalVerificationStatus.NOT_FOUND,
                retrieved_fields={},
                confidence=1.0,
                raw_response={"error": "no udyam_number supplied by bidder"},
            )

        # deterministic fake data keyed off the input so repeated calls
        # for the same bidder are stable during demo/testing
        seed = sum(ord(c) for c in udyam_number)
        is_edge_case = seed % 5 == 0  # ~20% of fake bidders hit an edge case

        if is_edge_case:
            return PortalVerificationResult(
                source=self.source_name,
                status=PortalVerificationStatus.SUCCESS,
                retrieved_fields={
                    "udyam_number": udyam_number,
                    "enterprise_name": bidder_data.get("legal_name", "UNKNOWN ENTERPRISE"),
                    "registration_status": "inactive",   # deliberate discrepancy for Layer 3 to catch
                    "category": "Small",
                },
                confidence=0.95,
                raw_response={"mock": True, "case": "inactive_registration"},
            )

        return PortalVerificationResult(
            source=self.source_name,
            status=PortalVerificationStatus.SUCCESS,
            retrieved_fields={
                "udyam_number": udyam_number,
                "enterprise_name": bidder_data.get("legal_name", "Test Enterprise"),
                "registration_status": "active",
                "category": "Micro",
            },
            confidence=0.98,
            raw_response={"mock": True, "case": "clean_match"},
        )