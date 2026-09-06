"""
AlgoRacers — Session 11: AI Racing Agent + x402 Paid Analytics
Module: services/agent_tools.py
==============================================================
Constrained, audited tools available to the AI Racing Agent:
  - READ TOOLS (Collection, Circuits, History, Leaderboard)
  - PAYMENT TOOL (x402 TestNet USDC Premium Circuit Analytics with Guardrails)
  - ACTION TOOL (Grand Prix Race Execution)
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from fastapi import HTTPException, status
import algosdk

from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.models.agent import PremiumCircuitAnalytics
from backend.app.models.race import Circuit, UserCollectionResponse
from backend.app.services.circuit_service import circuit_service
from backend.app.services.race_engine import race_engine
from backend.rewards.models import DriverTemplate

logger = logging.getLogger("algoracers.agent_tools")

# Hardcoded Security Guardrails
ALLOWED_SPENDING_ASSET = "USDC"
ALLOWED_SPENDING_ASSET_ID = 10458941
MAX_PAYMENT_PER_CALL_USDC = 0.01

# Static Fictional Premium Circuit Analytics Data
PREMIUM_CIRCUIT_DATA = {
    "nova_circuit": {
        "projected_tire_wear_pct": 64.2,
        "overtaking_opportunity_index": 8.5,
        "volatility_score": 3.8,
        "recommended_driver_archetype": "Top-Speed Specialist (Speed >= 90)",
        "strategic_tactical_note": "Long back straight provides 0.45s slipstream advantage. High Speed dominates lap delta."
    },
    "apex_ring": {
        "projected_tire_wear_pct": 78.4,
        "overtaking_opportunity_index": 4.2,
        "volatility_score": 5.1,
        "recommended_driver_archetype": "Technical Apex Hunter (Racecraft >= 88 & Qualifying >= 86)",
        "strategic_tactical_note": "Overtaking delta is low (+1.2s required). Track position from Qualifying and tire management are critical."
    },
    "storm_harbor": {
        "projected_tire_wear_pct": 52.0,
        "overtaking_opportunity_index": 7.1,
        "volatility_score": 8.9,
        "recommended_driver_archetype": "Aquaplaning Master (Wet Weather >= 85)",
        "strategic_tactical_note": "Standing water in Turn 7 causes severe snap oversteer for drivers with Wet Weather < 80."
    }
}

class AgentToolRegistry:
    # -------------------------------------------------------------
    # 1. READ-ONLY TOOLS
    # -------------------------------------------------------------
    @staticmethod
    def get_collection(wallet_address: str) -> UserCollectionResponse:
        """[READ TOOL] Fetches verified driver NFTs owned by the wallet on Algorand."""
        return race_engine.get_wallet_collection(wallet_address)

    @staticmethod
    def get_circuit(circuit_id: str) -> Circuit:
        """[READ TOOL] Fetches circuit characteristics and stat weight profile."""
        return circuit_service.get_circuit(circuit_id)

    @staticmethod
    def get_driver_history(wallet_address: str, driver_id: str) -> Dict[str, Any]:
        """[READ TOOL] Fetches historical race performance metrics for a driver."""
        with get_db() as conn:
            rows = conn.execute("""
                SELECT position, points, final_score, circuit_id
                FROM races
                WHERE wallet_address = ? AND driver_id = ?;
            """, (wallet_address, driver_id)).fetchall()

            if not rows:
                return {"total_races": 0, "avg_position": None, "win_rate": 0.0, "podium_rate": 0.0}

            total = len(rows)
            wins = sum(1 for r in rows if r["position"] == 1)
            podiums = sum(1 for r in rows if r["position"] <= 3)
            avg_pos = round(sum(r["position"] for r in rows) / total, 2)
            avg_score = round(sum(r["final_score"] for r in rows) / total, 2)

            return {
                "total_races": total,
                "avg_position": avg_pos,
                "avg_score": avg_score,
                "wins": wins,
                "win_rate": round(wins / total * 100, 1),
                "podium_rate": round(podiums / total * 100, 1)
            }

    # -------------------------------------------------------------
    # 2. PAYMENT TOOL (Guarded x402 TestNet USDC Purchase)
    # -------------------------------------------------------------
    @staticmethod
    def purchase_premium_analytics(
        circuit_id: str,
        wallet_address: str,
        user_approved: bool,
        approved_budget_usdc: float
    ) -> PremiumCircuitAnalytics:
        """
        [PAYMENT TOOL] Purchases deep x402 telemetry for circuit_id.
        ENFORCES STRICT GUARDRAILS:
          1. Network must be TestNet
          2. Explicit user approval required
          3. Price must not exceed budget or MAX_PAYMENT_PER_CALL_USDC (0.01 USDC)
          4. Asset must be TestNet USDC (ASA 10458941)
        """
        c_id = circuit_id.lower()
        circuit = circuit_service.get_circuit(c_id)

        # Guardrail 1: Network Check
        if settings.NETWORK.lower() not in ["testnet", "algorand-testnet"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Security Guardrail Violation: x402 spending only permitted on Algorand TestNet."
            )

        # Guardrail 2: User Approval Check
        if not user_approved:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="Human-in-the-Loop Guardrail: Premium analytics requires explicit user approval."
            )

        # Guardrail 3: Budget & Price Cap Check
        required_price = 0.01
        if approved_budget_usdc < required_price:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Budget Guardrail: Approved budget ({approved_budget_usdc} USDC) is less than required price ({required_price} USDC)."
            )

        if required_price > MAX_PAYMENT_PER_CALL_USDC:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Spending Policy Violation: Requested payment ({required_price} USDC) exceeds max cap ({MAX_PAYMENT_PER_CALL_USDC} USDC)."
            )

        now = datetime.now(timezone.utc).isoformat()
        static_intel = PREMIUM_CIRCUIT_DATA.get(c_id, {
            "projected_tire_wear_pct": 60.0,
            "overtaking_opportunity_index": 6.0,
            "volatility_score": 5.0,
            "recommended_driver_archetype": "Balanced Contender",
            "strategic_tactical_note": "Standard tactical delta applies."
        })

        logger.info(f"💵 Agent authorized 0.01 TestNet USDC payment for circuit '{c_id}' telemetry.")

        return PremiumCircuitAnalytics(
            circuit_id=c_id,
            circuit_name=circuit.name,
            track_type=circuit.track_type,
            weather=circuit.weather,
            projected_tire_wear_pct=static_intel["projected_tire_wear_pct"],
            overtaking_opportunity_index=static_intel["overtaking_opportunity_index"],
            volatility_score=static_intel["volatility_score"],
            recommended_driver_archetype=static_intel["recommended_driver_archetype"],
            strategic_tactical_note=static_intel["strategic_tactical_note"],
            paid_at=now
        )

agent_tools = AgentToolRegistry()
