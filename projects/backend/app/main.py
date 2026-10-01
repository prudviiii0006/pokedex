"""
Pokédex — Production Hardening, Logging & Observability
Module: main.py
=====================================================================
FastAPI application entrypoint with:
  - Startup TestNet Fail-Safe Network Guardrail
  - Request ID Correlation Middleware (X-Request-ID)
  - Process Latency Header (X-Process-Time-Ms)
  - Sanitized Error Handling
  - Structured Logging & Health/Readiness Routing
"""

import sys
import os
from pathlib import Path

_ws_root = Path(__file__).resolve().parent.parent.parent.parent
_backend_root = Path(__file__).resolve().parent.parent
_projects_root = Path(__file__).resolve().parent.parent.parent
for _p in [str(_ws_root), str(_backend_root), str(_projects_root)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

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
    health, packs, purchases, version,
    creatures, collection, battles, evolution, trades, activity, pricing, assets, fusion
)

# Setup structured logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [%(name)s]: %(message)s")
logger = logging.getLogger("pokedex.api")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Startup TestNet Fail-Safe Guardrail
    if settings.NETWORK.lower() not in ["testnet", "algorand-testnet"]:
        logger.critical(f"🛑 FATAL SECURITY VIOLATION: Pokédex is in Safe Learning Mode. Disallowed network '{settings.NETWORK}'. Refusing startup.")
        raise RuntimeError(f"Startup aborted: Only Algorand TestNet is permitted in Pokédex.")

    # 2. Database Initialization
    init_db()

    port = int(os.getenv("PORT", "8001"))
    logger.info(f"✨ Pokédex Core API started successfully! [Network: {settings.NETWORK}]")
    logger.info(f"📚 OpenAPI Documentation available at: http://localhost:{port}/docs")
    yield
    logger.info("🛑 Pokédex API shutting down cleanly.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="REST backend service for Pokédex: Pokémon digital collectibles, x402 payments, and ARC-3 NFT minting.",
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
    expose_headers=[
        "*",
        "X-Request-ID",
        "X-Process-Time-Ms",
        "payment-required",
        "Payment-Required",
        "PAYMENT-REQUIRED",
        "payment-response",
        "Payment-Response",
        "PAYMENT-RESPONSE",
        "WWW-Authenticate",
        "www-authenticate",
    ],
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
            "message": "An unexpected server error occurred. Please contact the Pokédex team.",
            "request_id": req_id
        }
    )

# 4. Mount Core MVP Direct Root-Level Endpoints
app.include_router(health.router, tags=["Health & Readiness"])
app.include_router(version.router, tags=["Version & Build Provenance"])
app.include_router(pricing.router, tags=["Authoritative Pricing & Config"])
app.include_router(packs.router, prefix="/packs", tags=["Packs & Rewards"])
app.include_router(purchases.router, tags=["Purchases & NFT Delivery"])
app.include_router(creatures.router, tags=["Creatures & Species Index"])
app.include_router(assets.router, tags=["On-Chain ASA NFT Verification"])
app.include_router(collection.router, tags=["Collection & Deck Management"])
app.include_router(battles.router, tags=["Arena Battles & Combat Engine"])
app.include_router(evolution.router, tags=["Creature Evolution Chamber"])
app.include_router(fusion.router, prefix="/fusion", tags=["Pokémon Fusion Chamber"])
app.include_router(trades.router, tags=["Peer-to-Peer Card Trading"])
app.include_router(activity.router, tags=["Activity & Live Feed"])

# 5. Versioned API Router (/api/v1)
app.include_router(api_router, prefix=settings.API_V1_STR)

if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.getenv("PORT", "8001"))
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=port, reload=False)
