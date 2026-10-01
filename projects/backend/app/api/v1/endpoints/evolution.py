import base64
import json
from fastapi import APIRouter, Path, Query, Body, Request, Response, HTTPException, status
from pydantic import BaseModel, Field
from backend.app.services.evolution_service import evolution_service
from backend.app.services.x402_service import x402_service
from backend.app.core.config import settings

router = APIRouter()

class EvolutionRequest(BaseModel):
    wallet_address: str = Field(..., examples=["3VZQZ4J4YRJBIJ6DAHGTS2QHZBLQUVKJYWRGHENSEIO5R73C5TFFL7N2PM"])
    asset_id: int = Field(..., examples=[742199042])

class BoostEvolutionRequest(BaseModel):
    wallet_address: str = Field(..., examples=["3VZQZ4J4YRJBIJ6DAHGTS2QHZBLQUVKJYWRGHENSEIO5R73C5TFFL7N2PM"])

@router.get(
    "/evolution/{asset_id}",
    summary="Check Evolution Eligibility (Free)",
    description="Queries whether an owned creature meets XP/Level thresholds to evolve."
)
async def check_evolution(
    asset_id: int = Path(..., description="Algorand ASA ID"),
    wallet_address: str = Query(..., description="Owner Wallet Address")
):
    return evolution_service.check_evolution_eligibility(asset_id, wallet_address)

@router.post(
    "/evolution/evolve",
    summary="Execute Creature Evolution (Free)",
    description="Validates prerequisites and permanently evolves the creature card to its next form with boosted stats."
)
async def evolve_creature(body: EvolutionRequest = Body(...)):
    return evolution_service.execute_evolution(body.asset_id, body.wallet_address)

from decimal import Decimal

@router.post(
    "/evolution/{asset_id}/boost",
    summary="Boost Creature Evolution XP (x402 Protected)",
    description="x402 protected endpoint: Grants a bounded +100 XP boost upon confirmed TestNet ALGO payment to accelerate evolution readiness."
)
async def boost_creature_evolution(
    request: Request,
    response: Response,
    asset_id: int = Path(..., description="Algorand ASA ID"),
    body: BoostEvolutionRequest = Body(...)
):
    resource_url = str(request.url)
    algo_price = getattr(settings, "EVOLUTION_BOOST_PRICE_ALGO", 0.02)
    amount_microalgos = int(Decimal(str(algo_price)) * Decimal("1000000"))
    description = f"Pokédex Instant Evolution Boost (+100 XP) — Asset #{asset_id}"

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

    result = evolution_service.boost_evolution(
        asset_id=asset_id,
        wallet_address=body.wallet_address,
        boost_xp=100
    )

    # Record in payment records
    x402_service.record_payment(
        wallet_address=body.wallet_address,
        resource_type="EVOLUTION_BOOST",
        resource_id=str(asset_id),
        amount_microalgos=amount_microalgos,
        payment_tx_id=receipt.get("transaction")
    )

    return result

