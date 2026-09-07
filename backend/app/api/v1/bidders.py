from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from core.database import get_db
from schemas.bidder_sc import BidderOut, BidderCreate
from models.bidder import Bidder


router = APIRouter(prefix="/bidders", tags=["bidders"])




@router.post("/", response_model=BidderOut)
def create_bidder(bidder: BidderCreate, db: Session = Depends(get_db)):
    db_bidder = Bidder(name=bidder.name, tender_id=bidder.tender_id)
    db.add(db_bidder)
    db.commit()
    db.refresh(db_bidder)
    return db_bidder

@router.get("/{bidder_id}", response_model=BidderOut)
def get_bidder(bidder_id: int, db: Session = Depends(get_db)):
    return db.query(Bidder).filter(Bidder.id == bidder_id).first()