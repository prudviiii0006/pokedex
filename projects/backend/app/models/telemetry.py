"""
AlgoRacers — Circuit Telemetry Models
Module: models/telemetry.py
=====================================
Pydantic schemas for Circuit Telemetry and Track Analysis.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field

class CircuitTelemetry(BaseModel):
    sector_1_delta: str
    sector_2_delta: str
    sector_3_delta: str
    tire_wear_optima: str
    recommended_pit_lap: int

class PremiumAnalysisResponse(BaseModel):
    title: str
    circuit: str
    track_conditions: str
    driver_telemetry: List[Dict[str, str]]
    tactical_ai_insights: str
    unlocked_at: str
    status: str = "AVAILABLE"
