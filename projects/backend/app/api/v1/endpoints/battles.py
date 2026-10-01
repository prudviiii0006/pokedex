import base64
import json
from typing import Optional, List
from fastapi import APIRouter, Body, Query, Request, Response, HTTPException, status
from pydantic import BaseModel, Field
from backend.app.services.battle_service import battle_service
from backend.app.services.x402_service import x402_service
from backend.app.core.config import settings

router = APIRouter()

class BattleRequest(BaseModel):
    wallet_address: str = Field(..., examples=["3VZQZ4J4YRJBIJ6DAHGTS2QHZBLQUVKJYWRGHENSEIO5R73C5TFFL7N2PM"])
    player_asset_id: int = Field(..., examples=[742199042], description="ASA ID of the owned creature card entering combat")
    arena_id: str = Field("volcano", examples=["volcano", "ocean", "sylvan", "thunder", "glacier"])
    strategy_id: str = Field("balanced", examples=["aggressive", "balanced", "defensive", "special"])

@router.get("/game/arenas", summary="Get All Battle Arenas")
async def get_arenas():
    return battle_service.get_arenas()

@router.get("/game/strategies", summary="Get All Combat Strategies")
async def get_strategies():
    return battle_service.get_strategies()

@router.post(
    "/game/battle",
    summary="Execute Free Arena Battle",
    description="Simulates turn-based combat with elemental multipliers and awards verified standard XP."
)
async def start_battle(body: BattleRequest = Body(...)):
    return battle_service.execute_battle(
        wallet_address=body.wallet_address,
        player_asset_id=body.player_asset_id,
        arena_id=body.arena_id,
        strategy_id=body.strategy_id,
        is_premium=False
    )

from decimal import Decimal

@router.post(
    "/game/battle/premium",
    summary="Execute Premium Arena Battle (x402 Protected)",
    description="x402 protected endpoint: Simulates tactical combat and awards +50 bonus XP upon confirmed TestNet ALGO payment."
)
async def start_premium_battle(
    request: Request,
    response: Response,
    body: BattleRequest = Body(...)
):
    resource_url = str(request.url)
    algo_price = getattr(settings, "PREMIUM_BATTLE_PRICE_ALGO", 0.02)
    amount_microalgos = int(Decimal(str(algo_price)) * Decimal("1000000"))
    description = f"Pokédex Premium Battle — {body.arena_id.capitalize()} Arena (+50 Bonus Combat XP)"

    payment_header = (
        request.headers.get("payment-signature") or 
        request.headers.get("PAYMENT-SIGNATURE") or 
        request.headers.get("x-402-payment-proof") or 
        request.headers.get("x-payment")
    )

    if not payment_header:
        challenge = x402_service.generate_challenge(
            resource_url=resource_url,
            description=description,
            amount_microalgos=amount_microalgos
        )
        b64_challenge = base64.b64encode(json.dumps(challenge).encode('utf-8')).decode('utf-8')
        headers = {
            "payment-required": b64_challenge,
            "WWW-Authenticate": "x402",
            "Cache-Control": "no-store",
            "Access-Control-Expose-Headers": "*, payment-required, payment-response, WWW-Authenticate"
        }
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=challenge,
            headers=headers
        )

    receipt = x402_service.verify_and_settle(
        payment_header=payment_header,
        resource_url=resource_url,
        required_amount_microalgos=amount_microalgos
    )
    b64_receipt = base64.b64encode(json.dumps(receipt).encode('utf-8')).decode('utf-8')
    response.headers["payment-response"] = b64_receipt

    # Execute battle with premium bonus XP
    battle_result = battle_service.execute_battle(
        wallet_address=body.wallet_address,
        player_asset_id=body.player_asset_id,
        arena_id=body.arena_id,
        strategy_id=body.strategy_id,
        is_premium=True,
        bonus_xp=50
    )

    # Record in payment records
    x402_service.record_payment(
        wallet_address=body.wallet_address,
        resource_type="PREMIUM_BATTLE",
        resource_id=battle_result["battle_id"],
        amount_microalgos=amount_microalgos,
        payment_tx_id=receipt.get("transaction")
    )

    return battle_result

@router.get(
    "/game/battle-history/{wallet_address}",
    summary="Get Player Battle History",
    description="Returns past arena battle encounters and logs for a wallet."
)
async def get_battle_history(
    wallet_address: str,
    limit: int = Query(20, ge=1, le=50)
):
    return battle_service.get_battle_history(wallet_address, limit=limit)
