import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel


class PortalVerificationStatus(str, Enum):
    SUCCESS = "success"
    NOT_FOUND = "not_found"
    UNAVAILABLE = "unavailable"   # timeout / circuit breaker tripped
    ERROR = "error"


class PortalVerificationResult(BaseModel):
    """
    The normalized contract every adapter must return, real or mocked.
    This is what makes swapping a mock for a real API a no-op for
    everything downstream — the orchestrator, repo, and scoring engine
    never see adapter-specific shapes, only this.
    """
    source: str                              # "udyam", "gstn", "digilocker", ...
    status: PortalVerificationStatus
    retrieved_fields: dict = {}              # normalized field:value pairs from the portal
    confidence: float = 1.0                  # 1.0 for deterministic portal lookups; lower if fuzzy-derived
    retrieved_at: datetime = datetime.now(timezone.utc)
    raw_response: dict = {}                  # unprocessed payload, kept for audit/debug


class PortalAdapter(ABC):
    """
    Every portal — real or mocked — implements this. The orchestrator
    only ever calls .verify(); it never knows or cares which subclass
    it's holding.
    """

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Short identifier used as portal_name in portal_responses, e.g. 'udyam'."""
        ...

    @abstractmethod
    async def verify(self, bidder_data: dict) -> PortalVerificationResult:
        """
        bidder_data is the bidder's company_details dict (GSTIN, PAN,
        udyam_number, etc. — whatever the bidder submitted). Each adapter
        pulls the fields it needs and ignores the rest.
        """
        ...