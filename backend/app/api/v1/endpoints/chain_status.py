"""
AlgoRacers — Session 21: Chain Synchronization & Health Endpoints
Module: api/v1/endpoints/chain_status.py
================================================================
Provides endpoints for monitoring Algod vs Indexer synchronization lag,
triggering subscriber sync batches, and auditing state reconciliation.
"""

from typing import Dict, Any, Optional
from fastapi import APIRouter, Query, Body, HTTPException, status
from pydantic import BaseModel, Field

from backend.app.chain.models import ChainSyncStatus, ReconciliationReport
from backend.app.chain.subscriber import chain_subscriber
from backend.app.chain.reconciliation import blockchain_reconciler

router = APIRouter()

class SyncBatchRequest(BaseModel):
    max_rounds: int = Field(50, examples=[50])

class ReconcileRequest(BaseModel):
    repair: bool = Field(False, examples=[False, True])

@router.get(
    "/status",
    response_model=ChainSyncStatus,
    summary="Get Chain Synchronization Health",
    description="Returns live Algod round, Indexer round, subscriber checkpoint, and lag metrics."
)
async def get_chain_sync_status():
    return chain_subscriber.get_sync_status()

@router.post(
    "/sync",
    summary="Trigger Subscriber Batch Synchronization",
    description="Polls Indexer and advances subscriber checkpoint by processing newly confirmed blocks."
)
async def trigger_sync_batch(body: SyncBatchRequest = Body(...)):
    return chain_subscriber.run_sync_batch(max_rounds=body.max_rounds)

@router.post(
    "/reconcile",
    response_model=ReconciliationReport,
    summary="Run Blockchain State Reconciliation Audit",
    description="Compares cached database state against canonical Algorand L1 ledger truth to detect drift."
)
async def run_reconciliation(body: ReconcileRequest = Body(...)):
    return blockchain_reconciler.run_reconciliation_audit(repair=body.repair)
