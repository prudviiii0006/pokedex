"""
AlgoRacers — Session 9: x402 Purchase Pipeline
Module: core/database.py
=============================================
Thread-safe SQLite persistence layer for purchase records and idempotency tracking.
Guarantees database-level unique constraints and ACID transaction safety.
"""

import sqlite3
from pathlib import Path
from contextlib import contextmanager
import logging

from backend.app.core.config import settings

logger = logging.getLogger("algoracers.database")

DB_PATH = settings.BASE_DIR / "data" / "algoracers.db"

def init_db():
    """Initializes SQLite schema with strict unique constraints."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_db() as conn:
        cursor = conn.cursor()
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
                metadata_uri TEXT,
                asset_id INTEGER UNIQUE,
                delivery_tx_id TEXT,
                status TEXT NOT NULL,
                error_message TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_wallet ON purchases(wallet_address);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_status ON purchases(status);")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS races (
                race_id TEXT PRIMARY KEY,
                idempotency_key TEXT UNIQUE,
                wallet_address TEXT NOT NULL,
                asset_id INTEGER NOT NULL,
                driver_id TEXT NOT NULL,
                driver_name TEXT NOT NULL,
                circuit_id TEXT NOT NULL,
                circuit_name TEXT NOT NULL,
                base_score REAL NOT NULL,
                variance REAL NOT NULL,
                final_score REAL NOT NULL,
                position INTEGER NOT NULL,
                points INTEGER NOT NULL,
                result_category TEXT NOT NULL,
                grid_results TEXT NOT NULL,
                analysis TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_race_wallet ON races(wallet_address);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_race_circuit ON races(circuit_id);")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS recommendations (
                recommendation_id TEXT PRIMARY KEY,
                wallet_address TEXT NOT NULL,
                circuit_id TEXT NOT NULL,
                recommended_asset_id INTEGER NOT NULL,
                recommended_driver_name TEXT NOT NULL,
                method TEXT NOT NULL,
                confidence REAL NOT NULL,
                reasoning_summary TEXT NOT NULL,
                factors TEXT NOT NULL,
                premium_used INTEGER NOT NULL,
                payment_tx_id TEXT,
                cost_usdc REAL NOT NULL,
                created_at TEXT NOT NULL
            );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_rec_wallet ON recommendations(wallet_address);")

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

        # Session 13: Authentication Challenges & Sessions Tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS auth_challenges (
                challenge_id TEXT PRIMARY KEY,
                wallet_address TEXT NOT NULL,
                nonce TEXT NOT NULL,
                domain TEXT NOT NULL,
                network TEXT NOT NULL,
                message_text TEXT NOT NULL,
                issued_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                used_at TEXT,
                status TEXT NOT NULL
            );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_challenge_wallet ON auth_challenges(wallet_address);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_challenge_status ON auth_challenges(status);")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                wallet_address TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL,
                revoked_at TEXT,
                is_active INTEGER NOT NULL DEFAULT 1
            );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_session_wallet ON sessions(wallet_address);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_session_active ON sessions(is_active);")

        # Session 14 & 15: On-Chain Tournament Registry with Verifiable Randomness
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tournaments (
                app_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                creator TEXT NOT NULL,
                circuit_id TEXT NOT NULL,
                max_players INTEGER NOT NULL,
                participant_count INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL,
                randomness_round INTEGER,
                randomness_value TEXT,
                race_engine_version TEXT DEFAULT 'v1',
                winner_asset_id INTEGER,
                result_hash TEXT,
                off_chain_result TEXT,
                created_at TEXT NOT NULL
            );
        """)
        # Safe migration for existing DB
        try:
            cursor.execute("ALTER TABLE tournaments ADD COLUMN randomness_round INTEGER;")
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("ALTER TABLE tournaments ADD COLUMN randomness_value TEXT;")
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("ALTER TABLE tournaments ADD COLUMN race_engine_version TEXT DEFAULT 'v1';")
        except sqlite3.OperationalError:
            pass
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tourn_status ON tournaments(status);")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tournament_participants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                app_id INTEGER NOT NULL,
                wallet_address TEXT NOT NULL,
                asset_id INTEGER NOT NULL,
                registered_at TEXT NOT NULL,
                UNIQUE(app_id, wallet_address),
                UNIQUE(app_id, asset_id),
                FOREIGN KEY(app_id) REFERENCES tournaments(app_id) ON DELETE CASCADE
            );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tp_app ON tournament_participants(app_id);")

        # Session 16: Player Profiles, Progression Ledger, Achievements & Reputation
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS player_profiles (
                wallet_address TEXT PRIMARY KEY,
                display_name TEXT,
                xp INTEGER NOT NULL DEFAULT 0,
                level INTEGER NOT NULL DEFAULT 1,
                reputation_score INTEGER NOT NULL DEFAULT 1000,
                races_completed INTEGER NOT NULL DEFAULT 0,
                wins INTEGER NOT NULL DEFAULT 0,
                podiums INTEGER NOT NULL DEFAULT 0,
                tournaments_entered INTEGER NOT NULL DEFAULT 0,
                tournaments_won INTEGER NOT NULL DEFAULT 0,
                drivers_owned INTEGER NOT NULL DEFAULT 0,
                achievement_count INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS progression_events (
                event_id TEXT PRIMARY KEY,
                wallet_address TEXT NOT NULL,
                event_type TEXT NOT NULL,
                source_type TEXT NOT NULL,
                source_id TEXT NOT NULL,
                xp_delta INTEGER NOT NULL,
                reason TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(source_type, source_id, wallet_address)
            );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pe_wallet ON progression_events(wallet_address);")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS player_achievements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                wallet_address TEXT NOT NULL,
                achievement_id TEXT NOT NULL,
                unlocked_at TEXT NOT NULL,
                source_event_id TEXT,
                credential_status TEXT NOT NULL DEFAULT 'OFF_CHAIN',
                credential_asset_id INTEGER,
                issuance_tx_id TEXT,
                UNIQUE(wallet_address, achievement_id)
            );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pa_wallet ON player_achievements(wallet_address);")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reputation_events (
                event_id TEXT PRIMARY KEY,
                wallet_address TEXT NOT NULL,
                source_type TEXT NOT NULL,
                source_id TEXT NOT NULL,
                rating_delta INTEGER NOT NULL,
                new_rating INTEGER NOT NULL,
                reason TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(source_type, source_id, wallet_address)
            );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_re_wallet ON reputation_events(wallet_address);")

        # Session 18: On-Chain Collection Registry Commitments
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS collection_registries (
                app_id INTEGER PRIMARY KEY,
                collection_id TEXT NOT NULL,
                version INTEGER NOT NULL,
                collection_root TEXT NOT NULL,
                leaf_count INTEGER NOT NULL,
                manifest_cid TEXT NOT NULL,
                publisher TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(collection_id, version)
            );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_cr_col_ver ON collection_registries(collection_id, version);")

        # Session 19: Seasons, Championship Series & Merkle Reward Claims
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS seasons (
                season_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                version INTEGER NOT NULL DEFAULT 1,
                status TEXT NOT NULL DEFAULT 'DRAFT',
                scoring_version TEXT NOT NULL DEFAULT 'v1',
                leaderboard_root TEXT,
                manifest_cid TEXT,
                player_count INTEGER NOT NULL DEFAULT 0,
                rounds_total INTEGER NOT NULL DEFAULT 4,
                app_id INTEGER,
                champion_wallet TEXT,
                created_at TEXT NOT NULL,
                finalized_at TEXT
            );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_seasons_status ON seasons(status);")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS season_tournaments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                season_id TEXT NOT NULL,
                app_id INTEGER NOT NULL,
                round_number INTEGER NOT NULL,
                processed_at TEXT,
                result_hash TEXT,
                UNIQUE(season_id, app_id),
                FOREIGN KEY(season_id) REFERENCES seasons(season_id) ON DELETE CASCADE
            );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_st_season ON season_tournaments(season_id);")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS season_leaderboard (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                season_id TEXT NOT NULL,
                wallet_address TEXT NOT NULL,
                driver_id TEXT,
                driver_name TEXT,
                rank INTEGER NOT NULL,
                points INTEGER NOT NULL DEFAULT 0,
                wins INTEGER NOT NULL DEFAULT 0,
                podiums INTEGER NOT NULL DEFAULT 0,
                tournaments_entered INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL,
                UNIQUE(season_id, wallet_address),
                FOREIGN KEY(season_id) REFERENCES seasons(season_id) ON DELETE CASCADE
            );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sl_season_rank ON season_leaderboard(season_id, rank);")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS season_claims (
                claim_id TEXT PRIMARY KEY,
                season_id TEXT NOT NULL,
                wallet_address TEXT NOT NULL,
                reward_id TEXT NOT NULL,
                rank INTEGER NOT NULL,
                credential_asset_id INTEGER,
                claim_tx_id TEXT,
                status TEXT NOT NULL DEFAULT 'UNCLAIMED',
                claimed_at TEXT,
                UNIQUE(season_id, wallet_address, reward_id),
                FOREIGN KEY(season_id) REFERENCES seasons(season_id) ON DELETE CASCADE
            );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sc_wallet ON season_claims(wallet_address);")

        # Session 20: Multisig Governance & Privileged Actions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS governance_proposals (
                proposal_id TEXT PRIMARY KEY,
                action_type TEXT NOT NULL,
                target_app_id INTEGER NOT NULL,
                sender_address TEXT NOT NULL,
                parameters_json TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'DRAFT',
                threshold_required INTEGER NOT NULL DEFAULT 2,
                signatures_count INTEGER NOT NULL DEFAULT 0,
                tx_hash TEXT,
                execution_tx_id TEXT,
                created_at TEXT NOT NULL,
                executed_at TEXT
            );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_gp_status ON governance_proposals(status);")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS governance_signatures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                proposal_id TEXT NOT NULL,
                signer_address TEXT NOT NULL,
                signature_hex TEXT NOT NULL,
                signed_at TEXT NOT NULL,
                UNIQUE(proposal_id, signer_address),
                FOREIGN KEY(proposal_id) REFERENCES governance_proposals(proposal_id) ON DELETE CASCADE
            );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_gs_proposal ON governance_signatures(proposal_id);")

        # Session 21: Algorand Indexer, Event Processing, Synchronization & Reconciliation
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chain_checkpoints (
                subscriber_name TEXT PRIMARY KEY,
                network TEXT NOT NULL,
                last_processed_round INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chain_events (
                event_id TEXT PRIMARY KEY,
                network TEXT NOT NULL,
                tx_id TEXT NOT NULL,
                round_number INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                app_id INTEGER,
                asset_id INTEGER,
                sender TEXT,
                receiver TEXT,
                payload_json TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'PROCESSED',
                created_at TEXT NOT NULL,
                processed_at TEXT NOT NULL,
                error_msg TEXT,
                UNIQUE(network, tx_id, event_type)
            );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ce_round ON chain_events(round_number);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ce_type ON chain_events(event_type);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ce_sender ON chain_events(sender);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ce_receiver ON chain_events(receiver);")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chain_sync_errors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT,
                error_type TEXT NOT NULL,
                details TEXT NOT NULL,
                occurred_at TEXT NOT NULL
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS deployment_registry (
                app_id INTEGER PRIMARY KEY,
                component_name TEXT NOT NULL,
                network TEXT NOT NULL,
                created_round INTEGER NOT NULL,
                version INTEGER NOT NULL DEFAULT 1,
                is_active INTEGER NOT NULL DEFAULT 1
            );
        """)

        # Session 22: PostgreSQL, Database Transactions, Background Jobs, Caching & Scaling
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY,
                job_type TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'PENDING',
                attempts INTEGER NOT NULL DEFAULT 0,
                max_attempts INTEGER NOT NULL DEFAULT 3,
                available_at TEXT NOT NULL,
                locked_at TEXT,
                locked_by TEXT,
                last_error TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status_avail ON jobs(status, available_at);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_type ON jobs(job_type);")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS outbox_events (
                outbox_id TEXT PRIMARY KEY,
                event_type TEXT NOT NULL,
                aggregate_type TEXT NOT NULL,
                aggregate_id TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'PENDING',
                created_at TEXT NOT NULL,
                dispatched_at TEXT
            );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_outbox_status ON outbox_events(status);")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS idempotency_records (
                idempotency_key TEXT PRIMARY KEY,
                scope TEXT NOT NULL,
                wallet_address TEXT,
                request_hash TEXT NOT NULL,
                response_json TEXT,
                status TEXT NOT NULL DEFAULT 'PROCESSING',
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL
            );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_idemp_wallet ON idempotency_records(wallet_address);")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cache_entries (
                cache_key TEXT PRIMARY KEY,
                cache_value TEXT NOT NULL,
                content_hash TEXT,
                is_immutable INTEGER NOT NULL DEFAULT 0,
                expires_at TEXT,
                created_at TEXT NOT NULL
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS race_simulation_batches (
                batch_id TEXT PRIMARY KEY,
                wallet_address TEXT NOT NULL,
                circuit_id TEXT NOT NULL,
                driver_id TEXT NOT NULL,
                simulations_count INTEGER NOT NULL,
                completed_count INTEGER NOT NULL DEFAULT 0,
                results_json TEXT,
                status TEXT NOT NULL DEFAULT 'PENDING',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sim_wallet ON race_simulation_batches(wallet_address);")

        # Session Redesign: Fusion & Atomic Trading Tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fusion_operations (
                fusion_id TEXT PRIMARY KEY,
                idempotency_key TEXT UNIQUE,
                wallet_address TEXT NOT NULL,
                status TEXT NOT NULL,
                input_asset_ids_json TEXT NOT NULL,
                output_asset_id INTEGER UNIQUE,
                premium_driver_id TEXT,
                premium_driver_name TEXT,
                premium_driver_team TEXT,
                metadata_uri TEXT,
                burn_tx_ids_json TEXT,
                delivery_tx_id TEXT,
                error_message TEXT,
                created_at TEXT NOT NULL,
                completed_at TEXT
            );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_fusion_wallet ON fusion_operations(wallet_address);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_fusion_status ON fusion_operations(status);")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fusion_inputs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fusion_id TEXT NOT NULL,
                asset_id INTEGER NOT NULL UNIQUE,
                wallet_address TEXT NOT NULL,
                driver_id TEXT NOT NULL,
                consumed_at TEXT NOT NULL,
                FOREIGN KEY(fusion_id) REFERENCES fusion_operations(fusion_id) ON DELETE CASCADE
            );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_fi_fusion ON fusion_inputs(fusion_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_fi_asset ON fusion_inputs(asset_id);")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trade_offers (
                trade_id TEXT PRIMARY KEY,
                creator_wallet TEXT NOT NULL,
                offered_asset_id INTEGER NOT NULL,
                offered_driver_id TEXT NOT NULL,
                offered_driver_name TEXT NOT NULL,
                offered_driver_team TEXT NOT NULL,
                offered_driver_rarity TEXT NOT NULL,
                requested_asset_id INTEGER NOT NULL,
                requested_driver_name TEXT NOT NULL,
                requested_driver_team TEXT,
                requested_driver_rarity TEXT,
                status TEXT NOT NULL DEFAULT 'OPEN',
                accepted_by TEXT,
                notes TEXT,
                atomic_group_id TEXT,
                execution_tx_ids_json TEXT,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                completed_at TEXT
            );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trade_status ON trade_offers(status);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trade_creator ON trade_offers(creator_wallet);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trade_offered ON trade_offers(offered_asset_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trade_requested ON trade_offers(requested_asset_id);")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS card_ownership_records (
                asset_id INTEGER PRIMARY KEY,
                driver_id TEXT NOT NULL,
                driver_name TEXT NOT NULL,
                team TEXT NOT NULL,
                rarity TEXT NOT NULL,
                current_owner TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'AVAILABLE',
                origin_type TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_card_owner ON card_ownership_records(current_owner);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_card_status ON card_ownership_records(status);")

        conn.commit()
    logger.info(f"📁 Database initialized at: {DB_PATH}")

@contextmanager
def get_db():
    """Context manager providing thread-safe SQLite connection with foreign keys and WAL mode."""
    conn = sqlite3.connect(str(DB_PATH), timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    try:
        yield conn
    finally:
        conn.close()

# Initialize DB on module load
init_db()
