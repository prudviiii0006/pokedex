"""
AlgoRacers — Session 10: Racing Mechanics & Leaderboard
Module: services/circuit_service.py
======================================================
Loads, parses, and validates circuit configurations and stat weights.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from fastapi import HTTPException, status

from backend.app.core.config import settings
from backend.app.models.race import Circuit

logger = logging.getLogger("algoracers.circuit_service")

CIRCUITS_FILE = settings.BASE_DIR / "data" / "circuits.json"

class CircuitService:
    def __init__(self, file_path: Path = CIRCUITS_FILE):
        self.file_path = file_path
        self._circuits: Dict[str, Circuit] = {}
        self.load_circuits()

    def load_circuits(self):
        """Loads and validates circuit definitions."""
        if not self.file_path.exists():
            raise FileNotFoundError(f"Circuits configuration file not found at: {self.file_path}")

        with open(self.file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self._circuits = {}
        for c in data:
            # Validate stat weights sum to 1.0 (with 0.001 float tolerance)
            weights_sum = sum(c["stat_weights"].values())
            if not (0.999 <= weights_sum <= 1.001):
                raise ValueError(
                    f"Circuit '{c['id']}' stat weights sum to {weights_sum:.4f}, but must equal 1.00 (100%)."
                )
            circuit = Circuit(**c)
            self._circuits[circuit.id] = circuit

        logger.info(f"🏁 Loaded {len(self._circuits)} racing circuits: {list(self._circuits.keys())}")

    def list_circuits(self) -> List[Circuit]:
        return list(self._circuits.values())

    def get_circuit(self, circuit_id: str) -> Circuit:
        c_id = circuit_id.lower()
        if c_id not in self._circuits:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Circuit '{circuit_id}' not found. Available circuits: {list(self._circuits.keys())}"
            )
        return self._circuits[c_id]

circuit_service = CircuitService()
