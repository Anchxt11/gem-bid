import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict

from backend.app.models.compliance_result import RequirementStatus, RiskLevel


class ComplianceResultCreate(BaseModel):
    bidder_id: uuid.UUID
    requirement_id: str
    status: RequirementStatus
    score: float | None = None
    risk_level: RiskLevel | None = None
    evidence: dict | None = None
    remarks: str | None = None


class ComplianceResultRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    result_id: uuid.UUID
    bidder_id: uuid.UUID
    requirement_id: str
    status: RequirementStatus
    score: float | None = None
    risk_level: RiskLevel | None = None
    evidence: dict | None = None
    remarks: str | None = None
    created_at: datetime


class ComplianceSummary(BaseModel):
    """Aggregated view for the dashboard's top-line card, not a DB row."""
    bidder_id: uuid.UUID
    overall_score: float
    overall_risk: RiskLevel
    results: list[ComplianceResultRead]