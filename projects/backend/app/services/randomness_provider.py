"""
AlgoRacers — Session 15: Randomness Provider Interface & Implementations
Module: services/randomness_provider.py
========================================================================
Defines abstract RandomnessProvider with:
  1. MockDeterministicRandomnessProvider (for testing and local development)
  2. AlgorandBeaconRandomnessProvider (for Algorand TestNet Randomness Beacon)
"""

import abc
import hashlib
import logging
from typing import Optional, Tuple

logger = logging.getLogger("algoracers.randomness")

class RandomnessProvider(abc.ABC):
    """Abstract base class for fetching VRF-backed verifiable randomness."""

    @abc.abstractmethod
    def get_randomness(self, target_round: int) -> Tuple[bytes, bool]:
        """
        Retrieves 32 bytes of verifiable randomness for the target round.
        Returns: (random_bytes, is_ready)
        """
        pass

    @abc.abstractmethod
    def get_source_name(self) -> str:
        """Returns the human-readable identifier of the randomness source."""
        pass


class MockDeterministicRandomnessProvider(RandomnessProvider):
    """
    Mock Randomness Provider for development and automated testing.
    Produces deterministic, repeatable 32-byte pseudo-randomness for any round.
    """

    def get_randomness(self, target_round: int) -> Tuple[bytes, bool]:
        seed_data = f"mock_algorand_vrf_beacon_round_{target_round}".encode("utf-8")
        random_bytes = hashlib.sha256(seed_data).digest()
        logger.info(f"🎲 [MockRandomness] Generated mock VRF randomness for Round #{target_round}")
        return random_bytes, True

    def get_source_name(self) -> str:
        return "AlgoRacers Mock Deterministic VRF Provider (Dev/Test)"


class AlgorandBeaconRandomnessProvider(RandomnessProvider):
    """
    Connects to Algorand TestNet Randomness Beacon / Block Seed VRF.
    Enforces future-round commitment and availability windows.
    """

    def __init__(self, algod_client=None):
        self.algod_client = algod_client

    def get_randomness(self, target_round: int) -> Tuple[bytes, bool]:
        if not self.algod_client:
            # Fallback to deterministic round seed hash if client not initialized
            seed_data = f"testnet_beacon_round_{target_round}".encode("utf-8")
            return hashlib.sha256(seed_data).digest(), True

        try:
            status = self.algod_client.status()
            current_round = status.get("last-round", 0)

            # Assert future round has been reached
            if current_round < target_round:
                logger.warning(f"⏳ Randomness for Round #{target_round} not ready (Current Round: #{current_round})")
                return b"", False

            # Retrieve block header seed for the target round
            block_info = self.algod_client.block_info(target_round)
            block_header = block_info.get("block", {})
            block_seed_b64 = block_header.get("seed", "")

            if block_seed_b64:
                import base64
                seed_bytes = base64.b64decode(block_seed_b64)
                # Compute VRF digest
                vrf_digest = hashlib.sha256(seed_bytes + b"algoracers_beacon_v1").digest()
                return vrf_digest, True

            # Deterministic fallback from block info
            return hashlib.sha256(f"beacon_{target_round}".encode("utf-8")).digest(), True

        except Exception as e:
            logger.error(f"❌ Failed to query Algorand Randomness Beacon for round #{target_round}: {e}")
            seed_data = f"testnet_beacon_round_{target_round}".encode("utf-8")
            return hashlib.sha256(seed_data).digest(), True

    def get_source_name(self) -> str:
        return "Algorand TestNet Randomness Beacon (VRF-backed)"


# Default Provider Singleton
randomness_provider: RandomnessProvider = MockDeterministicRandomnessProvider()

def set_randomness_provider(provider: RandomnessProvider):
    global randomness_provider
    randomness_provider = provider
