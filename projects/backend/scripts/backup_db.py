#!/usr/bin/env python3
"""
Pokédex — Database Backup CLI
Module: backend/scripts/backup_db.py
====================================
Creates a safe logical snapshot of the database.
Usage: python backup_db.py [output_path]
"""

import sys
import shutil
from pathlib import Path
from datetime import datetime, timezone

root_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(root_dir))

from backend.app.core.database import DB_PATH

def backup_database(destination: str = None):
    print("=" * 75)
    print("⚡  POKÉDEX — DATABASE BACKUP UTILITY")
    print("=" * 75)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_file = Path(destination) if destination else DB_PATH.parent / f"pokedex_backup_{timestamp}.db"

    shutil.copy2(DB_PATH, backup_file)
    print(f"✅ Source Database:  {DB_PATH}")
    print(f"📦 Backup Created:    {backup_file} ({backup_file.stat().st_size} bytes)")
    print("=" * 75)
    return backup_file

if __name__ == "__main__":
    dest = sys.argv[1] if len(sys.argv) > 1 else None
    backup_database(dest)
