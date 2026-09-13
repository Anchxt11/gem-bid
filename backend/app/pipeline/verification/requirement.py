"""
pipeline/verification/requirements.py

Static registry: one entry per Layer 2 portal, describing how Layer 3 should
read that portal's retrieved_fields and what Layer 4 requirement it maps to.

This exists because every mock adapter uses different field names for
conceptually the same thing (Udyam's "status", GSTN's "registration_status",
PAN's "pan_status" all mean the same thing: is this registration active).
Centralizing that mapping here means reconciliation.py has one generic
code path instead of nine hardcoded special cases — and adding a 10th
portal later is a one-entry addition here, not a new branch in the engine.
bidder_name_field exists for the same reason, but on the bidder's side —
every entry uses "legal_name" today, but a future entry can point to a
different bidder-submitted field without changing reconciliation logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class RequirementDefinition:
    portal_source: str  # matches PortalAdapter.source_name / PortalResponse.portal_name
    requirement_id: str
    requirement_name: str
    category: str
    mandatory: bool
    weight: float = 1.0
    kind: str = "registration"  # "registration" (status/validity + name check) | "listing" (debarment-style)

    # -- "registration" kind fields --
    name_field: str | None = None  # key in retrieved_fields holding the entity name
    status_field: str | None = None  # key holding an explicit status string, if the portal has one
    active_values: frozenset[str] = field(default_factory=lambda: frozenset({"active", "valid"}))
    date_field: str | None = None
    bidder_name_field: str = "legal_name"
    # key holding an ISO date; treated as expired if in the past


REQUIREMENTS: dict[str, RequirementDefinition] = {
    "udyam": RequirementDefinition(
        portal_source="udyam",
        requirement_id="udyam-001",
        requirement_name="Udyam/MSME Registration",
        category="udyam",
        mandatory=True,
        name_field="enterprise_name",
        status_field="status",
        bidder_name_field="something_else",
    ),
    "gstn": RequirementDefinition(
        portal_source="gstn",
        requirement_id="gstn-001",
        requirement_name="GST Registration",
        category="gstn",
        mandatory=True,
        name_field="legal_name",
        status_field="registration_status",
    ),
    "pan": RequirementDefinition(
        portal_source="pan",
        requirement_id="pan-001",
        requirement_name="PAN Verification",
        category="pan",
        mandatory=True,
        name_field="name_on_pan",
        status_field="pan_status",
        active_values=frozenset({"valid"}),
    ),
    "mca21": RequirementDefinition(
        portal_source="mca21",
        requirement_id="mca21-001",
        requirement_name="MCA21 Company Incorporation Status",
        category="mca21",
        mandatory=True,
        name_field="company_name",
        status_field="status",
    ),
    "epfo": RequirementDefinition(
        portal_source="epfo",
        requirement_id="epfo-001",
        requirement_name="EPFO Registration",
        category="epfo",
        mandatory=False,
        name_field="establishment_name",
        status_field="status",
    ),
    "esic": RequirementDefinition(
        portal_source="esic",
        requirement_id="esic-001",
        requirement_name="ESIC Registration",
        category="esic",
        mandatory=False,
        name_field="employer_name",
        status_field="status",
    ),
    "nsic": RequirementDefinition(
        portal_source="nsic",
        requirement_id="nsic-001",
        requirement_name="NSIC Single Point Registration",
        category="nsic",
        mandatory=False,
        name_field="unit_name",
        date_field="validity_upto",
    ),
    "startup_india": RequirementDefinition(
        portal_source="startup_india",
        requirement_id="startup-india-001",
        requirement_name="Startup India / DPIIT Recognition",
        category="startup_india",
        mandatory=False,
        name_field="entity_name",
        date_field="valid_upto",
    ),
    "debarment": RequirementDefinition(
        portal_source="debarment",
        requirement_id="debarment-001",
        requirement_name="Blacklisting/Debarment Check",
        category="blacklist",
        mandatory=True,
        kind="listing",
    ),
}
