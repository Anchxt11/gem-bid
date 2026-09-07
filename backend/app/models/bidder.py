from sqlalchemy import Column, Integer, String
from core.database import Base


class Bidder(Base):
    __tablename__ = "bidders"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    tender_id = Column(Integer)  # which tender this bidder belongs to