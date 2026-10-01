"""
Pokédex — FastAPI Backend
Module: models/health.py
=======================================
Pydantic schemas for health & diagnostics endpoints.
"""

from pydantic import BaseModel, Field

class HealthResponse(BaseModel):
    status: str = Field(..., examples=["ok"])
    service: str = Field(..., examples=["pokedex-api"])
    version: str = Field(..., examples=["1.0.0"])
    network: str = Field(..., examples=["testnet"])
