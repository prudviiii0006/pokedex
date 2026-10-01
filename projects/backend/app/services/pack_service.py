"""
Pokédex — FastAPI Backend
Module: services/pack_service.py
=======================================
Service layer keeping API routes thin.
Encapsulates RewardEngine operations and maps dataclasses to Pydantic responses.
"""

from typing import List, Optional
from fastapi import HTTPException, status
from backend.app.core.config import settings
from backend.app.models.pack import PackResponse
from backend.app.models.reward import RewardResponse, DriverSummary
from backend.rewards.engine import RewardEngine

class PackService:
    def __init__(self):
        try:
            self.engine = RewardEngine(
                packs_config_path=settings.PACKS_CONFIG_PATH,
                metadata_dir=settings.METADATA_DIR
            )
        except Exception as e:
            # Fallback for relative directory resolution
            self.engine = RewardEngine()

    def get_all_packs(self) -> List[PackResponse]:
        """Returns all configured packs as API responses."""
        packs = []
        for p in self.engine.packs.values():
            packs.append(PackResponse(
                id=p.id,
                name=p.name,
                price=p.price,
                currency=p.currency,
                reward_count=p.reward_count,
                description=p.description,
                rarities=p.rarities
            ))
        return packs

    def get_pack(self, pack_id: str) -> PackResponse:
        """Returns a single pack configuration or raises 404."""
        pack = self.engine.packs.get(pack_id.lower())
        if not pack:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Pack '{pack_id}' not found. Available packs: {list(self.engine.packs.keys())}"
            )
        return PackResponse(
            id=pack.id,
            name=pack.name,
            price=pack.price,
            currency=pack.currency,
            reward_count=pack.reward_count,
            description=pack.description,
            rarities=pack.rarities
        )

    def simulate_pack_opening(self, pack_id: str, wallet_address: Optional[str] = None) -> RewardResponse:
        """Executes a simulation roll and formats the Pydantic response."""
        if pack_id.lower() not in self.engine.packs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cannot simulate unknown pack '{pack_id}'."
            )

        try:
            reward_res = self.engine.open_pack(pack_id.lower(), purchase_id=wallet_address)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Reward generation failed: {str(e)}"
            )

        driver_data = reward_res.driver
        return RewardResponse(
            reward_id=reward_res.reward_id,
            pack_id=reward_res.pack_id,
            pack_name=reward_res.pack_name,
            rarity=reward_res.rarity,
            driver=DriverSummary(
                id=driver_data.id,
                name=driver_data.name,
                team=driver_data.team,
                rarity=driver_data.rarity,
                description=driver_data.description,
                image=driver_data.image,
                stats=driver_data.stats
            ),
            generated_at=reward_res.generated_at,
            is_simulation=True
        )

# Global singleton service instance
pack_service = PackService()
