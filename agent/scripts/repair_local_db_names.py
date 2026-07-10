import os
import json
import sqlite3
from pathlib import Path

def is_placeholder_name(name: str) -> bool:
    if not name:
        return True
    name_str = str(name).strip()
    if name_str.startswith("Stock ") or name_str.startswith("Stock"):
        return True
    if name_str.startswith("股票") and any(char.isdigit() for char in name_str):
        return True
    if name_str.startswith("代码") and any(char.isdigit() for char in name_str):
        return True
    if name_str.isdigit():
        return True
    return False

def load_static_names() -> dict:
    static_names = {}
    try:
        json_path = Path(__file__).resolve().parents[1] / "data" / "tdx_a_shares.json"
        if json_path.exists():
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for item in data.get("stocks", []):
                code = item.get("code", "")
                name = item.get("name", "")
                if code and name:
                    static_names[code] = name
            print(f"Loaded {len(static_names)} static names from tdx_a_shares.json")
    except Exception as e:
        print(f"Error loading tdx_a_shares.json: {e}")
    return static_names

def repair_db_file(db_path: Path, static_names: dict):
    print(f"\nScanning database: {db_path}")
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Get list of tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        repaired_count = 0
        
        # 1. Check stock_meta
        if "stock_meta" in tables:
            cursor.execute("SELECT code, name FROM stock_meta")
            rows = cursor.fetchall()
            for code, name in rows:
                if is_placeholder_name(name):
                    correct_name = static_names.get(code)
                    if correct_name:
                        cursor.execute("UPDATE stock_meta SET name = ? WHERE code = ?", (correct_name, code))
                        repaired_count += 1
            print(f"  - stock_meta table: repaired {repaired_count} placeholder names.")
            
        # 2. Check Watchlist
        if "Watchlist" in tables:
            watchlist_repaired = 0
            cursor.execute("SELECT code, name FROM Watchlist")
            rows = cursor.fetchall()
            for code, name in rows:
                # Watchlist code might be like '300750.SZ' or '300750'
                bare_code = code.split(".")[0].strip()
                if is_placeholder_name(name):
                    correct_name = static_names.get(bare_code)
                    if correct_name:
                        cursor.execute("UPDATE Watchlist SET name = ? WHERE code = ?", (correct_name, code))
                        watchlist_repaired += 1
            print(f"  - Watchlist table: repaired {watchlist_repaired} placeholder names.")
            repaired_count += watchlist_repaired
            
        if repaired_count > 0:
            conn.commit()
            print(f"  -> Changes committed successfully.")
        conn.close()
    except Exception as e:
        print(f"  Error repairing database {db_path}: {e}")

def main():
    static_names = load_static_names()
    if not static_names:
        print("No static names loaded, aborting database repair.")
        return
        
    # Resolve the active runtime root dynamically
    from src.config.paths import _get_active_runtime_dir
    db_root = _get_active_runtime_dir()
    if not db_root.exists():
        print(f"Database root {db_root} does not exist.")
        return
        
    db_files = list(db_root.glob("**/*.db"))
    print(f"Found {len(db_files)} database files in {db_root}")
    for db_path in db_files:
        repair_db_file(db_path, static_names)
        
if __name__ == "__main__":
    main()
