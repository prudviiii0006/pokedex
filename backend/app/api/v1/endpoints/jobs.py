"""
AlgoRacers — Session 22: Background Jobs & Outbox Endpoints
Module: api/v1/endpoints/jobs.py
===========================================================
Admin/Dev endpoints for inspecting job queue status, triggering outbox dispatch,
and retrying dead-letter failed jobs.
"""

import json
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Query, Path, HTTPException, status
from pydantic import BaseModel, Field

from backend.app.core.database import get_db
from backend.app.jobs.queue import job_queue
from backend.app.jobs.outbox import transactional_outbox

router = APIRouter()

class JobResponse(BaseModel):
    job_id: str
    job_type: str
    status: str
    attempts: int
    max_attempts: int
    available_at: str
    locked_by: Optional[str] = None
    last_error: Optional[str] = None
    created_at: str
    updated_at: str

class QueueMetricsResponse(BaseModel):
    pending_count: int
    running_count: int
    succeeded_count: int
    failed_count: int
    outbox_pending_count: int

@router.get(
    "",
    response_model=List[JobResponse],
    summary="List Background Jobs",
    description="Returns list of durable jobs filtered by status."
)
async def list_jobs(
    status: Optional[str] = Query(None, description="Filter by status (PENDING, RUNNING, SUCCEEDED, FAILED)"),
    limit: int = Query(50, ge=1, le=100)
):
    with get_db() as conn:
        if status:
            rows = conn.execute("""
                SELECT * FROM jobs WHERE status = ? ORDER BY created_at DESC LIMIT ?;
            """, (status, limit)).fetchall()
        else:
            rows = conn.execute("""
                SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?;
            """, (limit,)).fetchall()

        return [
            JobResponse(
                job_id=r["job_id"],
                job_type=r["job_type"],
                status=r["status"],
                attempts=r["attempts"],
                max_attempts=r["max_attempts"],
                available_at=r["available_at"],
                locked_by=r["locked_by"],
                last_error=r["last_error"],
                created_at=r["created_at"],
                updated_at=r["updated_at"]
            ) for r in rows
        ]

@router.get(
    "/metrics",
    response_model=QueueMetricsResponse,
    summary="Get Queue & Outbox Metrics",
    description="Returns aggregate queue counts across all job states."
)
async def get_queue_metrics():
    with get_db() as conn:
        p_cnt = conn.execute("SELECT COUNT(*) as c FROM jobs WHERE status = 'PENDING';").fetchone()["c"]
        r_cnt = conn.execute("SELECT COUNT(*) as c FROM jobs WHERE status = 'RUNNING';").fetchone()["c"]
        s_cnt = conn.execute("SELECT COUNT(*) as c FROM jobs WHERE status = 'SUCCEEDED';").fetchone()["c"]
        f_cnt = conn.execute("SELECT COUNT(*) as c FROM jobs WHERE status = 'FAILED';").fetchone()["c"]
        o_cnt = conn.execute("SELECT COUNT(*) as c FROM outbox_events WHERE status = 'PENDING';").fetchone()["c"]

        return QueueMetricsResponse(
            pending_count=p_cnt,
            running_count=r_cnt,
            succeeded_count=s_cnt,
            failed_count=f_cnt,
            outbox_pending_count=o_cnt
        )

@router.post(
    "/{job_id}/retry",
    summary="Retry Dead-Letter Job",
    description="Resets a permanently FAILED job back to PENDING."
)
async def retry_job(job_id: str = Path(...)):
    with get_db() as conn:
        res = conn.execute("""
            UPDATE jobs 
            SET status = 'PENDING', attempts = 0, last_error = NULL
            WHERE job_id = ?;
        """, (job_id,))
        conn.commit()
        if res.rowcount == 0:
            raise HTTPException(status_code=404, detail="Job not found")
    return {"message": f"Job #{job_id} reset to PENDING"}

@router.post(
    "/dispatch-outbox",
    summary="Trigger Outbox Dispatch",
    description="Flushes pending outbox events into the durable job queue."
)
async def trigger_outbox_dispatch():
    count = transactional_outbox.dispatch_pending()
    return {"dispatched_count": count}
