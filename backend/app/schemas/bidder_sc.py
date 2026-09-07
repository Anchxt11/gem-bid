from pydantic import BaseModel


class BidderCreate(BaseModel):
    name: str
    tender_id: int

class BidderOut(BaseModel):
    id: int
    name: str
    tender_id: int

    class Config:
        from_attributes = True   # lets Pydantic read SQLAlchemy objects directly