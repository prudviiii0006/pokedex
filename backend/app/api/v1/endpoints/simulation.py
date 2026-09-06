"""
AlgoRacers — Session 22: Durable Batch Race Simulation Endpoints
Module: api/v1/endpoints/simulation.py
================================================================
Asynchronous durable batch race simulation with idempotency protection.
"""

import json
import uuid
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Body, Header, Path, HTTPException, status
from pydantic import BaseModel, Field

from backend.app.core.database import get_db
from backend.app.jobs.queue import job_queue
from backend.app.services.idempotency_service import idempotency_service

router = APIRouter()

class CreateBatchSimulationRequest(BaseModel):
    wallet_address: str = Field(..., examples=["3VZQZ4J4YRJBIJ6DAHGTS2QHZBLQUVKJYWRGHENSEIO5R73C5TFFL7N2PM"])
    circuit_id: str = Field("monaco_gp", examples=["monaco_gp"])
    driver_id: str = Field("velocity_one", examples=["velocity_one"])
    simulations_count: int = Field(10, ge=1, le=1000, examples=[10])

class BatchSimulationResponse(BaseModel):
    batch_id: str
    wallet_address: str
    circuit_id: str
    driver_id: str
    simulations_count: int
    completed_count: int
    status: str
    results: Optional[List[Dict[str, Any]]] = None
    created_at: str

@router.post(
    "/batch",
    response_model=BatchSimulationResponse,
    summary="Create Durable Batch Race Simulation",
    description="Enqueues a background job to run 1-1,000 deterministic race simulations."
)
async def create_batch_simulation(
    body: CreateBatchSimulationRequest = Body(...),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key")
):
    req_dict = body.model_dump()

    # 1. Idempotency Check
    if idempotency_key:
        is_new, cached_res = idempotency_service.check_or_reserve(
            idempotency_key=idempotency_key,
            scope="race_batch_simulation",
            wallet_address=body.wallet_address,
            request_body=req_dict
        )
        if not is_new and cached_res:
            return cached_res

    batch_id = f"batch_{uuid.uuid4().hex[:12]}"
    now_iso = "2026-08-30T16:00:00Z"

    with get_db() as conn:
        conn.execute("""
            INSERT INTO race_simulation_batches (
                batch_id, wallet_address, circuit_id, driver_id,
                simulations_count, completed_count, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, 0, 'PENDING', ?, ?);
        """, (
            batch_id, body.wallet_address, body.circuit_id, body.driver_id,
            body.simulations_count, now_iso, now_iso
        ))
        conn.commit()

    # 2. Enqueue background job
    job_queue.enqueue(
        job_type="RACE_SIMULATION_BATCH",
        payload={
            "batch_id": batch_id,
            "circuit_id": body.circuit_id,
            "driver_id": body.driver_id,
            "simulations_count": body.simulations_count
        }
    )

    resp_data = BatchSimulationResponse(
        batch_id=batch_id,
        wallet_address=body.wallet_address,
        circuit_id=body.circuit_id,
        driver_id=body.driver_id,
        simulations_count=body.simulations_count,
        completed_count=0,
        status="PENDING",
        created_at=now_iso
    )

    if idempotency_key:
        idempotency_service.store_response(
            idempotency_key=idempotency_key,
            scope="race_batch_simulation",
            response_data=resp_data.model_dump()
        )

    return resp_data

@router.get(
    "/batches/{batch_id}",
    response_model=BatchSimulationResponse,
    summary="Get Batch Simulation Status",
    description="Returns progress and results for a simulation batch."
)
async def get_batch_simulation(batch_id: str = Path(...)):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM race_simulation_batches WHERE batch_id = ?;", (batch_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Batch not found")

        results = json.loads(row["results_json"]) if row["results_json"] else None
        return BatchSimulationResponse(
            batch_id=row["batch_id"],
            wallet_address=row["wallet_address"],
            circuit_id=row["circuit_id"],
            driver_id=row["driver_id"],
            simulations_count=row["simulations_count"],
            completed_count=row["completed_count"],
            status=row["status"],
            results=results,
            created_at=row["created_at"]
        )
