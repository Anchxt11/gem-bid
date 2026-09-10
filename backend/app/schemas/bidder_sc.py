import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict

from backend.app.models.bidder import BidderStatus


class BidderBase(BaseModel):
    company_details: dict
    contact_info: dict


class BidderCreate(BidderBase):
    pass


class BidderUpdate(BaseModel):
    company_details: dict | None = None
    contact_info: dict | None = None
    status: BidderStatus | None = None


class BidderRead(BidderBase):
    model_config = ConfigDict(from_attributes=True)

    bidder_id: uuid.UUID
    status: BidderStatus
    created_at: datetime
    updated_at: datetime