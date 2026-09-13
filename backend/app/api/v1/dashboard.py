import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func, case, literal
from sqlalchemy.orm import selectinload
from backend.app.core.database import AsyncSessionLocal
from backend.app.models.bidder import Bidder
from backend.app.models.compliance_result import ComplianceResult, RiskLevel, RequirementStatus

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _summarize_compliance(compliance_results: list) -> tuple[float | None, str | None]:
    """Compute overall score and risk level from a set of compliance results.

    Returns (score, risk_level) — both None if no results exist yet.
    """
    if not compliance_results:
        return None, None

    # All rows from a single verification run share the same score/risk_level
    # (the orchestrator writes the same overall score to every row).
    # But be defensive: average all non-null scores.
    scores = [cr.score for cr in compliance_results if cr.score is not None]
    overall_score = round(sum(scores) / len(scores), 2) if scores else None

    # Risk level: worst wins
    risk_levels = [cr.risk_level for cr in compliance_results if cr.risk_level is not None]
    if not risk_levels:
        risk_level_str = None
    elif any(rl == RiskLevel.HIGH for rl in risk_levels):
        risk_level_str = "High"
    elif any(rl == RiskLevel.MEDIUM for rl in risk_levels):
        risk_level_str = "Medium"
    else:
        risk_level_str = "Low"

    return overall_score, risk_level_str


def _latest_compliance_results(all_results: list) -> list:
    """Return only the most recent set of compliance results.

    Each verification run writes one row per requirement, all at roughly the
    same timestamp. We group by created_at (rounded to the second) and keep
    only the latest batch, so stale results from previous runs don't
    accumulate in the UI.
    """
    if not all_results:
        return []

    # Find the latest created_at timestamp
    latest_ts = max(cr.created_at for cr in all_results)

    # Keep results within 5 seconds of the latest (a single run's rows)
    cutoff = latest_ts.timestamp() - 5
    return [cr for cr in all_results if cr.created_at.timestamp() >= cutoff]


@router.get("/summary")
async def list_bidders_summary():
    """Return all bidders with their latest compliance score and risk level.

    Used by the officer-bidders.html list page to show real data instead of
    random placeholder values.
    """
    async with AsyncSessionLocal() as session:
        stmt = (
            select(Bidder)
            .options(selectinload(Bidder.compliance_results))
            .order_by(Bidder.created_at.desc())
        )
        result = await session.execute(stmt)
        bidders = list(result.scalars().all())

        summaries = []
        for b in bidders:
            latest_crs = _latest_compliance_results(list(b.compliance_results))
            score, risk_level = _summarize_compliance(latest_crs)

            summaries.append({
                "bidder_id": str(b.bidder_id),
                "company_details": b.company_details,
                "contact_info": b.contact_info,
                "status": b.status.value,
                "created_at": b.created_at.isoformat(),
                "score": score,
                "risk_level": risk_level,
            })

        return summaries


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

        # Only use the LATEST verification run's results
        latest_crs = _latest_compliance_results(list(bidder.compliance_results))
        score, risk_level = _summarize_compliance(latest_crs)

        return {
            "bidder_id": str(bidder.bidder_id),
            "company_details": bidder.company_details,
            "contact_info": bidder.contact_info,
            "status": bidder.status.value,
            "created_at": bidder.created_at.isoformat(),
            "score": score,
            "risk_level": risk_level,
            "compliance_results": [
                {
                    "requirement_id": cr.requirement_id,
                    "status": cr.status.value,
                    "score": cr.score,
                    "risk_level": cr.risk_level.value if cr.risk_level else None,
                    "evidence": cr.evidence,
                    "remarks": cr.remarks
                } for cr in latest_crs
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
                } for d in bidder.documents
            ]
        }
