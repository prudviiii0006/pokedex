"""
AlgoRacers — Session 10: Racing Mechanics & Leaderboard
Module: api/v1/endpoints/circuits.py
===================================================
Endpoints for discovering racing circuits and stat weight profiles.
"""

from typing import List
from fastapi import APIRouter, Path
from backend.app.models.race import Circuit
from backend.app.services.circuit_service import circuit_service

router = APIRouter()

@router.get(
    "/circuits",
    response_model=List[Circuit],
    summary="List Racing Circuits",
    description="Retrieves all available circuits, track types, weather conditions, and stat weighting profiles."
)
async def list_circuits():
    return circuit_service.list_circuits()

@router.get(
    "/circuits/{circuit_id}",
    response_model=Circuit,
    summary="Get Circuit by ID",
    description="Retrieves a specific circuit configuration and its stat weights."
)
async def get_circuit(
    circuit_id: str = Path(..., examples=["nova_circuit"], description="Circuit identifier ('nova_circuit', 'apex_ring', 'storm_harbor')")
):
    return circuit_service.get_circuit(circuit_id)
