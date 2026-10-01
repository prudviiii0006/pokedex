"""
Pokédex — FastAPI Backend
Module: models/pack.py
=======================================
Pydantic schemas for pack configurations.
"""

from typing import Dict
from pydantic import BaseModel, Field

class PackResponse(BaseModel):
    id: str = Field(..., examples=["basic"], description="Unique pack identifier")
    name: str = Field(..., examples=["Basic Pack"], description="Display title of the pack")
    price: float = Field(..., examples=[0.1], description="Pack price in specified currency (ALGO)")
    currency: str = Field(..., examples=["ALGO"], description="Currency ticker (e.g. ALGO)")
    reward_count: int = Field(..., examples=[1], description="Number of items rewarded")
    description: str = Field(..., examples=["Standard driver pack with solid contenders."])
    rarities: Dict[str, float] = Field(
        ..., 
        examples=[{"Common": 65.0, "Rare": 25.0, "Epic": 9.0, "Legendary": 1.0}],
        description="Probability distribution table summing to 100%"
    )
