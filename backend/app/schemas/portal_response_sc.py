import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict

from backend.app.models.portal_response import PortalStatus


class PortalResponseCreate(BaseModel):
    bidder_id: uuid.UUID
    portal_name: str
    status: PortalStatus
    response_data: dict | None = None


class PortalResponseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    response_id: uuid.UUID
    bidder_id: uuid.UUID
    portal_name: str
    status: PortalStatus
    response_data: dict | None = None
    fetched_at: datetime