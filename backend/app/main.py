"""
AlgoRacers — Session 12: Production Hardening, Logging & Observability
Module: main.py
=====================================================================
FastAPI application entrypoint with:
  - Startup TestNet Fail-Safe Network Guardrail
  - Request ID Correlation Middleware (X-Request-ID)
  - Process Latency Header (X-Process-Time-Ms)
  - Sanitized Error Handling
  - Structured Logging & Health/Readiness Routing
"""

import time
import uuid
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.core.config import settings
from backend.app.core.database import init_db
from backend.app.api.v1.api import api_router
from backend.app.api.v1.endpoints import (
    health, auth, packs, premium,
    purchases, circuits, races, agent,
    tournaments, profile, achievements, collections, seasons, governance,
    chain_status, activity, jobs, simulation, version,
    fusion, trading
)

# Setup structured logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [%(name)s]: %(message)s")
logger = logging.getLogger("algoracers.api")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Startup TestNet Fail-Safe Guardrail
    if settings.NETWORK.lower() not in ["testnet", "algorand-testnet"]:
        logger.critical(f"🛑 FATAL SECURITY VIOLATION: AlgoRacers is in Safe Learning Mode. Disallowed network '{settings.NETWORK}'. Refusing startup.")
        raise RuntimeError(f"Startup aborted: Only Algorand TestNet is permitted in AlgoRacers.")

    # 2. Database Initialization
    init_db()

    logger.info(f"🏎️  AlgoRacers API started successfully! [Network: {settings.NETWORK}]")
    logger.info(f"📚 OpenAPI Documentation available at: http://localhost:8000/docs")
    yield
    logger.info("🛑 AlgoRacers API shutting down cleanly.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="REST backend service for AlgoRacers: x402 payments, driver collectibles, race engine, and AI agent.",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# 1. Configure CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Request ID, Security Headers & Body Limit Middleware
@app.middleware("http")
async def security_and_observability_middleware(request: Request, call_next):
    req_id = request.headers.get("X-Request-ID") or f"req_{uuid.uuid4().hex[:12]}"
    request.state.request_id = req_id

    # 1. Enforce Request Body Size Limit (1MB)
    content_length = request.headers.get("Content-Length")
    if content_length and int(content_length) > 1_048_576:
        return JSONResponse(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            content={
                "error": "PayloadTooLarge",
                "message": "Request payload exceeds maximum allowed size of 1MB.",
                "request_id": req_id
            }
        )
    
    start_time = time.perf_counter()
    response = await call_next(request)
    process_time = (time.perf_counter() - start_time) * 1000

    # 2. Observability Headers
    response.headers["X-Request-ID"] = req_id
    response.headers["X-Process-Time-Ms"] = f"{process_time:.2f}"

    # 3. Security Headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response

# 3. Global Exception Handler (Safe, Sanitized Error Reporting)
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    req_id = getattr(request.state, "request_id", "unknown")
    logger.error(f"[ReqID: {req_id}] Unhandled error at {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "InternalServerError",
            "message": "An unexpected server error occurred. Please contact the AlgoRacers team.",
            "request_id": req_id
        }
    )

# 4. Mount Direct Root-Level Endpoints
app.include_router(health.router, tags=["Health & Readiness"])
app.include_router(version.router, tags=["Version & Build Provenance"])
app.include_router(auth.router, prefix="/auth", tags=["Wallet Authentication"])
app.include_router(packs.router, prefix="/packs", tags=["Packs & Rewards"])
app.include_router(premium.router, tags=["x402 Paid Resources"])
app.include_router(purchases.router, tags=["Purchases & NFT Delivery"])
app.include_router(circuits.router, tags=["Circuits"])
app.include_router(races.router, tags=["Racing & Leaderboard"])
app.include_router(fusion.router, tags=["Card Fusion Lab"])
app.include_router(trading.router, tags=["Trading Marketplace"])
app.include_router(agent.router, tags=["AI Racing Agent"])
app.include_router(tournaments.router, prefix="/tournaments", tags=["On-Chain Tournaments"])
app.include_router(profile.router, tags=["Player Profile & Progression"])
app.include_router(achievements.router, prefix="/achievements", tags=["Achievements"])
app.include_router(collections.router, prefix="/collections", tags=["Collection Commitments & Merkle Proofs"])
app.include_router(seasons.router, prefix="/seasons", tags=["Championship Seasons & Merkle Claims"])
app.include_router(governance.router, prefix="/governance", tags=["Multisig Governance & Privileged Controls"])
app.include_router(chain_status.router, prefix="/chain", tags=["Chain Synchronization & Health"])
app.include_router(activity.router, prefix="/activity", tags=["On-Chain Activity Feed"])
app.include_router(jobs.router, prefix="/jobs", tags=["Durable Background Jobs"])
app.include_router(simulation.router, prefix="/races", tags=["Batch Race Simulation"])

# 5. Versioned API Router (/api/v1)
app.include_router(api_router, prefix=settings.API_V1_STR)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=False)
