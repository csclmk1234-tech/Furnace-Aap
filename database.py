import sqlite3
import pandas as pd
from datetime import datetime

DB_PATH = "tmt_furnace_16t.db"

def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS heats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                log_date TEXT NOT NULL,
                shift TEXT NOT NULL,
                lining_campaign INTEGER NOT NULL,
                lining_heat_no INTEGER NOT NULL,
                heat_no INTEGER NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                start_kwh INTEGER NOT NULL,
                end_kwh INTEGER NOT NULL,
                start_kvah INTEGER NOT NULL,
                end_kvah INTEGER NOT NULL,
                actual_kwh INTEGER NOT NULL,
                actual_kvah INTEGER NOT NULL,
                calc_pf REAL NOT NULL,
                inst_pf REAL NOT NULL,
                tapped_tons REAL NOT NULL,
                sec_kwh_ton REAL NOT NULL,
                kvah_per_ton REAL NOT NULL,
                run_condition TEXT NOT NULL,
                holding_mins INTEGER NOT NULL,
                est_holding_kwh REAL NOT NULL,
                extra_loss_kwh REAL NOT NULL,
                low_pf_extra_kvah REAL NOT NULL,
                benchmark_sec REAL NOT NULL,
                entry_mode TEXT DEFAULT 'SINGLE',
                created_at TEXT NOT NULL
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS plant_state (
                key TEXT PRIMARY KEY,
                val TEXT NOT NULL
            )
        """)
        defaults = {
            "lining_campaign": "1",
            "lining_heat_count": "0",
            "benchmark_sec": "580.0"
        }
        for k, v in defaults.items():
            c.execute("INSERT OR IGNORE INTO plant_state (key, val) VALUES (?, ?)", (k, v))
        conn.commit()

def get_state(key: str, default: str = "") -> str:
    with get_conn() as conn:
        row = conn.execute("SELECT val FROM plant_state WHERE key = ?", (key,)).fetchone()
        return row[0] if row else default

def set_state(key: str, val: str):
    with get_conn() as conn:
        conn.execute("INSERT OR REPLACE INTO plant_state (key, val) VALUES (?, ?)", (key, str(val)))
        conn.commit()

def reset_lining_campaign():
    curr_camp = int(get_state("lining_campaign", "1"))
    set_state("lining_campaign", str(curr_camp + 1))
    set_state("lining_heat_count", "0")
    return curr_camp + 1

def get_last_heat():
    with get_conn() as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM heats ORDER BY id DESC LIMIT 1").fetchone()
        return dict(row) if row else None

def insert_heat(record: dict):
    cols = [
        "log_date", "shift", "lining_campaign", "lining_heat_no", "heat_no",
        "start_time", "end_time", "start_kwh", "end_kwh", "start_kvah", "end_kvah",
        "actual_kwh", "actual_kvah", "calc_pf", "inst_pf", "tapped_tons",
        "sec_kwh_ton", "kvah_per_ton", "run_condition", "holding_mins",
        "est_holding_kwh", "extra_loss_kwh", "low_pf_extra_kvah",
        "benchmark_sec", "entry_mode", "created_at"
    ]
    record["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    placeholders = ", ".join(["?"] * len(cols))
    col_names = ", ".join(cols)
    values = [record[c] for c in cols]

    with get_conn() as conn:
        conn.execute(f"INSERT INTO heats ({col_names}) VALUES ({placeholders})", values)
        conn.commit()
    set_state("lining_heat_count", str(record["lining_heat_no"]))

def insert_bulk_heats(records: list):
    for r in records:
        insert_heat(r)

def fetch_heats_df() -> pd.DataFrame:
    with get_conn() as conn:
        return pd.read_sql_query("SELECT * FROM heats ORDER BY id DESC", conn)

def delete_heat_by_id(heat_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM heats WHERE id = ?", (heat_id,))
        conn.commit()
# DONE_DB
