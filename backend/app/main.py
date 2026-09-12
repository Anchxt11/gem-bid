from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.app.api.v1 import bidders, documents, audit, verify, dashboard

app = FastAPI(title="GeM Bid Compliance Verification Platform")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(bidders.router, prefix="/api/v1")
app.include_router(documents.router, prefix="/api/v1")
app.include_router(audit.router, prefix="/api/v1")
app.include_router(verify.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")

@app.get("/health")
async def health():
    return {"status": "ok"}

import os
if os.path.exists("frontend"):
    app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")