from fastapi import FastAPI

from backend.app.api.v1 import bidders, documents, audit, verify

app = FastAPI(title="GeM Bid Compliance Verification Platform")

app.include_router(bidders.router, prefix="/api/v1")
app.include_router(documents.router, prefix="/api/v1")
app.include_router(audit.router, prefix="/api/v1")
app.include_router(verify.router, prefix="/api/v1")

@app.get("/health")
async def health():
    return {"status": "ok"}