from backend.app.pipeline.portal_integration.adapters.mock_debarment import MockDebarmentAdapter
from backend.app.pipeline.portal_integration.adapters.mock_epfo import MockEPFOAdapter
from backend.app.pipeline.portal_integration.adapters.mock_esic import MockESICAdapter
from backend.app.pipeline.portal_integration.adapters.mock_gstn import MockGSTNAdapter
from backend.app.pipeline.portal_integration.adapters.mock_mca21 import MockMCA21Adapter
from backend.app.pipeline.portal_integration.adapters.mock_nsic import MockNSICAdapter
from backend.app.pipeline.portal_integration.adapters.mock_pan import MockPANAdapter
from backend.app.pipeline.portal_integration.adapters.mock_startup_india import MockStartupIndiaAdapter
from backend.app.pipeline.portal_integration.adapters.mock_udyam import MockUdyamAdapter

__all__ = [
    "MockUdyamAdapter",
    "MockGSTNAdapter",
    "MockPANAdapter",
    "MockEPFOAdapter",
    "MockESICAdapter",
    "MockMCA21Adapter",
    "MockNSICAdapter",
    "MockStartupIndiaAdapter",
    "MockDebarmentAdapter",
]

# Registry the orchestrator can iterate over with asyncio.gather without
# hardcoding adapter names in verification_orchestrator.py. Each entry is
# (adapter_instance, required bidder_input keys) so the orchestrator can
# build the per-adapter input slice from a full bidder record.
ALL_MOCK_ADAPTERS: list[tuple[object, list[str]]] = [
    (MockUdyamAdapter(), ["udyam_number", "legal_name"]),
    (MockGSTNAdapter(), ["gstin", "legal_name"]),
    (MockPANAdapter(), ["pan_number", "legal_name"]),
    (MockEPFOAdapter(), ["epfo_establishment_id", "legal_name"]),
    (MockESICAdapter(), ["esic_code", "legal_name"]),
    (MockMCA21Adapter(), ["cin", "legal_name"]),
    (MockNSICAdapter(), ["nsic_registration_number", "legal_name"]),
    (MockStartupIndiaAdapter(), ["dpiit_recognition_number", "legal_name"]),
    (MockDebarmentAdapter(), ["pan_number"]),
]
