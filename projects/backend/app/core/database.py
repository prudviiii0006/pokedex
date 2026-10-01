"""
Pokédex — Database Module
=====================================================
Thread-safe SQLite persistence layer for Purchases, x402 Settlements,
Owned Creatures, Battles, Dynamic Evolutions, and Atomic Trades.
Guarantees database-level unique constraints and ACID transaction safety.
"""

import sqlite3
from pathlib import Path
from contextlib import contextmanager
import logging

from backend.app.core.config import settings

logger = logging.getLogger("pokedex.database")

DB_PATH = settings.BASE_DIR / "data" / "pokedex.db"

def init_db():
    """Initializes SQLite schema with full creature game support & backwards compatibility."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_db() as conn:
        cursor = conn.cursor()
        
        # 1. Core Pack Purchases Table (Backward compatible + Creature columns)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS purchases (
                purchase_id TEXT PRIMARY KEY,
                idempotency_key TEXT UNIQUE,
                pack_id TEXT NOT NULL,
                wallet_address TEXT NOT NULL,
                price_usdc REAL NOT NULL,
                payment_status TEXT NOT NULL,
                payment_tx_id TEXT UNIQUE,
                reward_status TEXT NOT NULL,
                reward_id TEXT UNIQUE,
                rarity TEXT,
                driver_id TEXT,
                driver_name TEXT,
                creature_id TEXT,
                creature_name TEXT,
                creature_type TEXT,
                metadata_uri TEXT,
                asset_id INTEGER UNIQUE,
                delivery_tx_id TEXT,
                status TEXT NOT NULL,
                error_message TEXT,
                schema_version TEXT DEFAULT 'CREATURE_V1',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_wallet ON purchases(wallet_address);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_status ON purchases(status);")

        # Migrate existing table columns if necessary
        for col, col_type in [
            ("creature_id", "TEXT"),
            ("creature_name", "TEXT"),
            ("creature_type", "TEXT"),
            ("schema_version", "TEXT DEFAULT 'CREATURE_V1'"),
            ("mint_tx_id", "TEXT"),
            ("mint_round", "INTEGER DEFAULT 0"),
            ("network", "TEXT DEFAULT 'testnet'"),
            ("mint_status", "TEXT DEFAULT 'NOT_STARTED'"),
            ("delivery_status", "TEXT DEFAULT 'NOT_STARTED'")
        ]:
            try:
                cursor.execute(f"ALTER TABLE purchases ADD COLUMN {col} {col_type};")
            except sqlite3.OperationalError:
                pass

        # 2. x402 Payment Settlements Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS x402_settlements (
                payment_tx_id TEXT PRIMARY KEY,
                payer_address TEXT NOT NULL,
                pay_to_address TEXT NOT NULL,
                amount_micro_usdc INTEGER NOT NULL,
                asset_id INTEGER NOT NULL,
                resource_url TEXT NOT NULL,
                status TEXT NOT NULL,
                settled_at TEXT NOT NULL
            );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_x402_payer ON x402_settlements(payer_address);")

        # 3. Owned Creatures Table (Dynamic NFT Progression State)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS owned_creatures (
                asset_id INTEGER PRIMARY KEY,
                wallet_address TEXT NOT NULL,
                template_id TEXT NOT NULL,
                name TEXT NOT NULL,
                primary_type TEXT NOT NULL,
                secondary_type TEXT,
                faction TEXT NOT NULL,
                rarity TEXT NOT NULL,
                level INTEGER NOT NULL DEFAULT 1,
                xp INTEGER NOT NULL DEFAULT 0,
                hp INTEGER NOT NULL,
                attack INTEGER NOT NULL,
                defense INTEGER NOT NULL,
                speed INTEGER NOT NULL,
                stamina INTEGER NOT NULL,
                battle_wins INTEGER NOT NULL DEFAULT 0,
                battle_losses INTEGER NOT NULL DEFAULT 0,
                evolution_stage INTEGER NOT NULL DEFAULT 1,
                mint_tx TEXT,
                delivery_tx TEXT,
                metadata_uri TEXT,
                pokemon_id INTEGER,
                ownership_verified INTEGER DEFAULT 1,
                network TEXT DEFAULT 'testnet',
                purchase_id TEXT,
                acquired_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_owned_wallet ON owned_creatures(wallet_address);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_owned_template ON owned_creatures(template_id);")

        for col, col_type in [
            ("delivery_tx", "TEXT"),
            ("metadata_uri", "TEXT"),
            ("pokemon_id", "INTEGER"),
            ("ownership_verified", "INTEGER DEFAULT 1"),
            ("network", "TEXT DEFAULT 'testnet'")
        ]:
            try:
                cursor.execute(f"ALTER TABLE owned_creatures ADD COLUMN {col} {col_type};")
            except sqlite3.OperationalError:
                pass

        # 4. Arena Battles Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS battles (
                battle_id TEXT PRIMARY KEY,
                wallet_address TEXT NOT NULL,
                player_asset_id INTEGER NOT NULL,
                player_creature_name TEXT NOT NULL,
                opponent_template_id TEXT NOT NULL,
                opponent_creature_name TEXT NOT NULL,
                arena_id TEXT NOT NULL,
                strategy TEXT NOT NULL,
                winner TEXT NOT NULL,
                player_xp_gained INTEGER NOT NULL DEFAULT 0,
                is_premium INTEGER NOT NULL DEFAULT 0,
                bonus_xp INTEGER NOT NULL DEFAULT 0,
                level_up INTEGER NOT NULL DEFAULT 0,
                new_level INTEGER,
                rounds_log_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_battle_wallet ON battles(wallet_address);")

        # 5. Evolutions Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS creature_evolutions (
                evolution_id TEXT PRIMARY KEY,
                asset_id INTEGER NOT NULL,
                wallet_address TEXT NOT NULL,
                from_template_id TEXT NOT NULL,
                to_template_id TEXT NOT NULL,
                from_stage INTEGER NOT NULL,
                to_stage INTEGER NOT NULL,
                evolved_at TEXT NOT NULL
            );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_evo_asset ON creature_evolutions(asset_id);")

        # 6. Peer-to-Peer Trades Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                trade_id TEXT PRIMARY KEY,
                initiator_wallet TEXT NOT NULL,
                initiator_asset_id INTEGER NOT NULL,
                counterparty_wallet TEXT,
                counterparty_asset_id INTEGER,
                status TEXT NOT NULL,
                featured_until TEXT,
                created_at TEXT NOT NULL,
                settled_at TEXT
            );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_status ON trades(status);")

        try:
            cursor.execute("ALTER TABLE trades ADD COLUMN featured_until TEXT;")
        except sqlite3.OperationalError:
            pass

        try:
            cursor.execute("ALTER TABLE battles ADD COLUMN is_premium INTEGER DEFAULT 0;")
        except sqlite3.OperationalError:
            pass

        try:
            cursor.execute("ALTER TABLE battles ADD COLUMN bonus_xp INTEGER DEFAULT 0;")
        except sqlite3.OperationalError:
            pass

        # 7. Unified Payment Records Table (x402 Resource Ledger)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS payment_records (
                payment_id TEXT PRIMARY KEY,
                wallet_address TEXT NOT NULL,
                resource_type TEXT NOT NULL,
                resource_id TEXT NOT NULL,
                network TEXT NOT NULL,
                asset_id INTEGER NOT NULL,
                amount_micro_usdc INTEGER NOT NULL,
                payment_tx_id TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_payrec_wallet ON payment_records(wallet_address);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_payrec_resource ON payment_records(resource_type, resource_id);")

        # 8. Fusion Records Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fusions (
                fusion_id TEXT PRIMARY KEY,
                wallet_address TEXT NOT NULL,
                status TEXT NOT NULL,
                input_count INTEGER NOT NULL DEFAULT 5,
                transfer_tx_id TEXT,
                reward_pokemon_id INTEGER,
                reward_name TEXT,
                reward_type TEXT,
                reward_rarity TEXT DEFAULT 'Legendary',
                reward_asset_id INTEGER UNIQUE,
                delivery_tx_id TEXT,
                error_message TEXT,
                created_at TEXT NOT NULL,
                completed_at TEXT
            );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_fusion_wallet ON fusions(wallet_address);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_fusion_status ON fusions(status);")

        # 9. Fusion Inputs Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fusion_inputs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fusion_id TEXT NOT NULL,
                input_asset_id INTEGER NOT NULL,
                pokemon_id INTEGER,
                name TEXT,
                rarity TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'PENDING',
                FOREIGN KEY (fusion_id) REFERENCES fusions(fusion_id) ON DELETE CASCADE
            );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_finput_fusion ON fusion_inputs(fusion_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_finput_asset ON fusion_inputs(input_asset_id);")

        conn.commit()
        logger.info(f"AlgoCreatures SQLite Database initialized at: {DB_PATH}")

@contextmanager
def get_db():
    """
    Context manager for thread-safe SQLite connection.
    Automatically handles commit on success and rollback on exception.
    """
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False, timeout=15.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Database error occurred: {e}")
        raise
    finally:
        conn.close()

# Auto-initialize database tables and migrations on import
init_db()

