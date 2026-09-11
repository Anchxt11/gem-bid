from backend.app.pipeline.scoring.base import MatchStatus, RequirementCheck, score_bidder


def print_report(report):
    print(f"\n{'=' * 70}")
    print(f"Bidder: {report.bidder_id}")
    print(f"Overall Score: {report.overall_score}%")
    print(f"Risk Level: {report.risk_level.value.upper()}")
    print(f"Recommendation: {report.recommendation}")
    print(f"{'-' * 70}")
    for r in report.requirement_results:
        flag = "MANDATORY" if r.mandatory else "optional"
        print(f"  [{r.status.value.upper():12}] ({flag:9}) {r.requirement_name}")
        print(f"      -> {r.reason}")
    print(f"{'=' * 70}")


# --- Scenario 1: clean bidder, everything checks out -----------------------

clean_bidder = [
    RequirementCheck(
        requirement_id="udyam-001",
        requirement_name="Udyam/MSME Registration",
        category="udyam",
        mandatory=True,
        match_status=MatchStatus.MATCH,
        extraction_confidence=0.97,
        portal_confidence=0.99,
        evidence_refs=["doc:udyam_cert.pdf"],
    ),
    RequirementCheck(
        requirement_id="gst-001",
        requirement_name="GST Registration",
        category="gstn",
        mandatory=True,
        match_status=MatchStatus.MATCH,
        extraction_confidence=0.95,
        portal_confidence=0.98,
        evidence_refs=["doc:gst_cert.pdf"],
    ),
    RequirementCheck(
        requirement_id="pan-001",
        requirement_name="PAN Verification",
        category="pan",
        mandatory=True,
        match_status=MatchStatus.MINOR_DISCREPANCY,
        bidder_value="ABCDE1234F",
        portal_value="abcde1234f",
        extraction_confidence=0.9,
        portal_confidence=0.95,
        evidence_refs=["doc:pan_card.jpg"],
        notes="Case mismatch only",
    ),
    RequirementCheck(
        requirement_id="blacklist-001",
        requirement_name="Blacklisting/Debarment Check",
        category="blacklist",
        mandatory=True,
        match_status=MatchStatus.MATCH,
        portal_confidence=1.0,
        evidence_refs=["portal:debarment_registry"],
    ),
]

# --- Scenario 2: shaky bidder, needs review but nothing disqualifying ------

shaky_bidder = [
    RequirementCheck(
        requirement_id="udyam-001",
        requirement_name="Udyam/MSME Registration",
        category="udyam",
        mandatory=True,
        match_status=MatchStatus.MATCH,
        extraction_confidence=0.92,
        portal_confidence=0.9,
        evidence_refs=["doc:udyam_cert.pdf"],
    ),
    RequirementCheck(
        requirement_id="gst-001",
        requirement_name="GST Registration",
        category="gstn",
        mandatory=True,
        match_status=MatchStatus.PORTAL_UNAVAILABLE,
        evidence_refs=["doc:gst_cert.pdf"],
        notes="GSTN sandbox aggregator timed out",
    ),
    RequirementCheck(
        requirement_id="epfo-001",
        requirement_name="EPFO Registration",
        category="epfo",
        mandatory=False,
        match_status=MatchStatus.UNVERIFIABLE,
        extraction_confidence=0.55,
        evidence_refs=["doc:epfo_challan.pdf"],
    ),
    RequirementCheck(
        requirement_id="blacklist-001",
        requirement_name="Blacklisting/Debarment Check",
        category="blacklist",
        mandatory=True,
        match_status=MatchStatus.MATCH,
        portal_confidence=1.0,
        evidence_refs=["portal:debarment_registry"],
    ),
]

# --- Scenario 3: ineligible bidder, mandatory GST fails --------------------

ineligible_bidder = [
    RequirementCheck(
        requirement_id="udyam-001",
        requirement_name="Udyam/MSME Registration",
        category="udyam",
        mandatory=True,
        match_status=MatchStatus.MATCH,
        extraction_confidence=0.96,
        portal_confidence=0.97,
        evidence_refs=["doc:udyam_cert.pdf"],
    ),
    RequirementCheck(
        requirement_id="gst-001",
        requirement_name="GST Registration",
        category="gstn",
        mandatory=True,
        match_status=MatchStatus.MAJOR_DISCREPANCY,
        bidder_value="27ABCDE1234F1Z5",
        portal_value="27XYZAB9876K1Z2",
        extraction_confidence=0.9,
        portal_confidence=0.95,
        evidence_refs=["doc:gst_cert.pdf"],
        notes="GSTIN on document does not match any portal record for this PAN",
    ),
    RequirementCheck(
        requirement_id="blacklist-001",
        requirement_name="Blacklisting/Debarment Check",
        category="blacklist",
        mandatory=True,
        match_status=MatchStatus.MATCH,
        portal_confidence=1.0,
        evidence_refs=["portal:debarment_registry"],
    ),
]

if __name__ == "__main__":
    print_report(score_bidder("BIDDER-CLEAN-001", clean_bidder))
    print_report(score_bidder("BIDDER-SHAKY-002", shaky_bidder))
    print_report(score_bidder("BIDDER-INELIGIBLE-003", ineligible_bidder))
