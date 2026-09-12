import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from backend.app.core.database import AsyncSessionLocal
from backend.app.models.bidder import Bidder

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

@router.get("/{bidder_id}")
async def get_bidder_dashboard(bidder_id: uuid.UUID):
    async with AsyncSessionLocal() as session:
        stmt = (
            select(Bidder)
            .options(
                selectinload(Bidder.compliance_results),
                selectinload(Bidder.portal_responses),
                selectinload(Bidder.documents)
            )
            .where(Bidder.bidder_id == bidder_id)
        )
        result = await session.execute(stmt)
        bidder = result.scalar_one_or_none()
        
        if not bidder:
            raise HTTPException(status_code=404, detail="Bidder not found")
            
        # Calculate a mock score since there's no actual AI scoring engine yet
        # If they have verified compliance, bump score up.
        cr_scores = [cr.score for cr in bidder.compliance_results if cr.score is not None]
        overall_score = sum(cr_scores) / len(cr_scores) if cr_scores else 60.0
        
        # Decide risk level based on compliance results
        risk_level = "Medium"
        if any(cr.risk_level == "high" for cr in bidder.compliance_results):
            risk_level = "High"
        elif all(cr.risk_level == "low" for cr in bidder.compliance_results):
            risk_level = "Low"
            
        return {
            "bidder_id": str(bidder.bidder_id),
            "company_details": bidder.company_details,
            "contact_info": bidder.contact_info,
            "status": bidder.status.value,
            "created_at": bidder.created_at.isoformat(),
            "score": round(overall_score, 1),
            "risk_level": risk_level,
            "compliance_results": [
                {
                    "requirement_id": cr.requirement_id,
                    "status": cr.status.value,
                    "score": cr.score,
                    "risk_level": cr.risk_level.value if cr.risk_level else None,
                    "evidence": cr.evidence,
                    "remarks": cr.remarks
                } for cr in bidder.compliance_results
            ],
            "portal_responses": [
                {
                    "portal_name": pr.portal_name,
                    "status": pr.status.value,
                    "fetched_at": pr.fetched_at.isoformat(),
                    "response_data": pr.response_data
                } for pr in bidder.portal_responses
            ],
            "documents": [
                {
                    "doc_id": str(d.doc_id),
                    "doc_type": d.doc_type.value,
                    "file_path": d.file_path,
                    "status": d.status.value
                } for d in bidder.documents
            ]
        }
