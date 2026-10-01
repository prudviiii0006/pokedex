import base64
import json
from typing import Optional, List
from fastapi import APIRouter, Body, Path, Query, Request, Response, HTTPException, status
from pydantic import BaseModel, Field
from backend.app.services.trade_service import trade_service
from backend.app.services.x402_service import x402_service
from backend.app.core.config import settings

router = APIRouter()

class CreateTradeRequest(BaseModel):
    initiator_wallet: str = Field(..., examples=["3VZQZ4J4YRJBIJ6DAHGTS2QHZBLQUVKJYWRGHENSEIO5R73C5TFFL7N2PM"])
    initiator_asset_id: int = Field(..., examples=[742199042])
    counterparty_wallet: Optional[str] = Field(None, description="Optional target wallet for direct private trades")
    counterparty_asset_id: Optional[int] = Field(None, description="Optional requested specific ASA ID")

class AcceptTradeRequest(BaseModel):
    counterparty_wallet: str = Field(..., examples=["GZSTVC3KHF3QQ77CCQFHXL3CYFCM4ANFRJOIC3TUHQKI2STM25BC7IAZU4"])
    counterparty_asset_id: int = Field(..., examples=[742199099])

class FeatureTradeRequest(BaseModel):
    wallet_address: str = Field(..., examples=["3VZQZ4J4YRJBIJ6DAHGTS2QHZBLQUVKJYWRGHENSEIO5R73C5TFFL7N2PM"])

@router.get("/trades", summary="List Active Trading Offers")
async def list_trades():
    return trade_service.list_trades()

@router.post("/trades", summary="Create Trade Offer (Free)")
async def create_trade(body: CreateTradeRequest = Body(...)):
    return trade_service.create_trade(
        initiator_wallet=body.initiator_wallet,
        initiator_asset_id=body.initiator_asset_id,
        counterparty_wallet=body.counterparty_wallet,
        counterparty_asset_id=body.counterparty_asset_id
    )

@router.post("/trades/{trade_id}/accept", summary="Accept and Settle Trade (Free)")
async def accept_trade(
    trade_id: str = Path(..., description="Unique trade offer ID"),
    body: AcceptTradeRequest = Body(...)
):
    return trade_service.accept_trade(
        trade_id=trade_id,
        counterparty_wallet=body.counterparty_wallet,
        counterparty_asset_id=body.counterparty_asset_id
    )

from decimal import Decimal

@router.post(
    "/trades/{trade_id}/feature",
    summary="Feature Trade Listing for 24h (x402 Protected)",
    description="x402 protected endpoint: Pins trade offer to top of marketplace for 24h upon confirmed TestNet ALGO payment."
)
async def feature_trade(
    request: Request,
    response: Response,
    trade_id: str = Path(..., description="Unique trade offer ID"),
    body: FeatureTradeRequest = Body(...)
):
    resource_url = str(request.url)
    algo_price = getattr(settings, "FEATURED_TRADE_PRICE_ALGO", 0.01)
    amount_microalgos = int(Decimal(str(algo_price)) * Decimal("1000000"))
    description = f"Pokédex 24h Featured Trade Pin — Trade #{trade_id}"

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

    result = trade_service.feature_trade(trade_id=trade_id, wallet_address=body.wallet_address)

    # Record in payment records
    x402_service.record_payment(
        wallet_address=body.wallet_address,
        resource_type="FEATURED_TRADE",
        resource_id=trade_id,
        amount_microalgos=amount_microalgos,
        payment_tx_id=receipt.get("transaction")
    )

    return result

@router.get(
    "/trades/smart-match",
    summary="Smart Trade Matcher (x402 Protected)",
    description="x402 protected endpoint: Analyzes collection gaps and matches active community listings based on elemental synergy upon confirmed TestNet ALGO payment."
)
async def smart_match_trades(
    request: Request,
    response: Response,
    wallet_address: str = Query(..., description="Trainer Wallet Address")
):
    resource_url = str(request.url)
    algo_price = getattr(settings, "SMART_MATCH_PRICE_ALGO", 0.01)
    amount_microalgos = int(Decimal(str(algo_price)) * Decimal("1000000"))
    description = f"Pokédex Smart Trade Match Analysis for {wallet_address[:8]}..."

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

    result = trade_service.smart_match(wallet_address=wallet_address)

    # Record in payment records
    x402_service.record_payment(
        wallet_address=wallet_address,
        resource_type="SMART_MATCH",
        resource_id=f"match_{wallet_address[:10]}_{int(receipt.get('timestamp', 0))}",
        amount_microalgos=amount_microalgos,
        payment_tx_id=receipt.get("transaction")
    )

    return result

