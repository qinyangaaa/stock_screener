"""SQLite 数据库模型 — 存储每日推荐结果"""

import sqlite3
import json
from datetime import date, datetime
from pathlib import Path
from typing import Optional


DB_PATH = Path(__file__).resolve().parent.parent / "stock_screener.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS screening_runs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id     TEXT NOT NULL UNIQUE,
            status      TEXT NOT NULL DEFAULT 'running',
            started_at  TEXT NOT NULL,
            finished_at TEXT,
            total_stocks INTEGER DEFAULT 0,
            passed_stage1 INTEGER DEFAULT 0,
            passed_all   INTEGER DEFAULT 0,
            error       TEXT,
            details_json TEXT
        );

        CREATE TABLE IF NOT EXISTS recommendations (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id      INTEGER NOT NULL REFERENCES screening_runs(id),
            rank        INTEGER NOT NULL,
            code        TEXT NOT NULL,
            name        TEXT NOT NULL,
            score       REAL NOT NULL,
            signal      TEXT NOT NULL,  -- 'strong_buy', 'buy', 'watch'
            change_pct  REAL,
            volume_ratio REAL,
            turnover    REAL,
            market_cap  REAL,
            rule_details TEXT,  -- JSON: 每条规则通过情况
            created_at  TEXT NOT NULL,
            screening_date TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS strategy_config (
            key         TEXT PRIMARY KEY,
            value       TEXT NOT NULL,
            description TEXT,
            updated_at  TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_rec_date ON recommendations(screening_date);
        CREATE INDEX IF NOT EXISTS idx_rec_code ON recommendations(code);
    """)
    conn.commit()
    conn.close()


def save_screening_run(task_id: str, status: str = "running") -> int:
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO screening_runs (task_id, status, started_at) VALUES (?, ?, ?)",
        (task_id, status, datetime.now().isoformat()),
    )
    conn.commit()
    run_id = cur.lastrowid
    conn.close()
    return run_id


def update_screening_run(run_id: int, **kwargs):
    if not kwargs:
        return
    sets = ", ".join(f"{k}=?" for k in kwargs)
    conn = get_connection()
    conn.execute(
        f"UPDATE screening_runs SET {sets} WHERE id=?",
        (*kwargs.values(), run_id),
    )
    conn.commit()
    conn.close()


def save_recommendations(run_id: int, stocks: list, screening_date: str):
    """stocks: list of dicts with keys matching recommendations columns"""
    conn = get_connection()
    now = datetime.now().isoformat()
    rows = [
        (
            run_id, s["rank"], s["code"], s["name"], s["score"],
            s["signal"], s.get("change_pct"), s.get("volume_ratio"),
            s.get("turnover"), s.get("market_cap"),
            json.dumps(s.get("rule_details", {}), ensure_ascii=False),
            now, screening_date,
        )
        for s in stocks
    ]
    conn.executemany(
        """INSERT INTO recommendations
           (run_id, rank, code, name, score, signal, change_pct,
            volume_ratio, turnover, market_cap, rule_details, created_at, screening_date)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        rows,
    )
    conn.commit()
    conn.close()


def get_latest_recommendations() -> list:
    conn = get_connection()
    rows = conn.execute(
        """SELECT * FROM recommendations
           WHERE screening_date = (SELECT MAX(screening_date) FROM recommendations)
           ORDER BY rank ASC"""
    ).fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


def get_recommendations_by_date(screening_date: str) -> list:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM recommendations WHERE screening_date=? ORDER BY rank ASC",
        (screening_date,),
    ).fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


def get_recommendation_dates() -> list:
    conn = get_connection()
    rows = conn.execute(
        "SELECT DISTINCT screening_date FROM recommendations ORDER BY screening_date DESC"
    ).fetchall()
    conn.close()
    return [r["screening_date"] for r in rows]


def get_latest_run_status() -> Optional[dict]:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM screening_runs ORDER BY id DESC LIMIT 1"
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_run_by_task_id(task_id: str) -> Optional[dict]:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM screening_runs WHERE task_id=?", (task_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_stock_detail(code: str, limit: int = 5) -> list:
    conn = get_connection()
    rows = conn.execute(
        """SELECT * FROM recommendations WHERE code=?
           ORDER BY screening_date DESC LIMIT ?""",
        (code, limit),
    ).fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


def save_screening_details(run_id: int, details: dict):
    """将筛选明细 JSON 写入 screening_runs.details_json"""
    conn = get_connection()
    conn.execute(
        "UPDATE screening_runs SET details_json=? WHERE id=?",
        (json.dumps(details, ensure_ascii=False), run_id),
    )
    conn.commit()
    conn.close()


def get_screening_runs(limit: int = 30) -> list:
    """获取最近的筛选运行记录"""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM screening_runs ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_screening_details(run_id: int = None, task_id: str = None) -> dict:
    """获取筛选明细"""
    conn = get_connection()
    if run_id:
        row = conn.execute("SELECT details_json FROM screening_runs WHERE id=?", (run_id,)).fetchone()
    elif task_id:
        row = conn.execute("SELECT details_json FROM screening_runs WHERE task_id=?", (task_id,)).fetchone()
    else:
        row = conn.execute("SELECT details_json FROM screening_runs ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()
    if row and row["details_json"]:
        return json.loads(row["details_json"])
    return {}


def get_all_config() -> dict:
    """读取所有策略配置"""
    conn = get_connection()
    rows = conn.execute("SELECT key, value FROM strategy_config").fetchall()
    conn.close()
    return {r["key"]: r["value"] for r in rows}


def save_config(key: str, value, description: str = None):
    """保存单个策略配置"""
    conn = get_connection()
    now = datetime.now().isoformat()
    conn.execute(
        """INSERT INTO strategy_config (key, value, description, updated_at)
           VALUES (?, ?, ?, ?)
           ON CONFLICT(key) DO UPDATE SET value=excluded.value,
                                         description=COALESCE(excluded.description, description),
                                         updated_at=excluded.updated_at""",
        (key, str(value), description, now),
    )
    conn.commit()
    conn.close()


def save_config_batch(items: dict):
    """批量保存配置项 {key: value, ...}"""
    conn = get_connection()
    now = datetime.now().isoformat()
    for key, value in items.items():
        conn.execute(
            """INSERT INTO strategy_config (key, value, updated_at)
               VALUES (?, ?, ?)
               ON CONFLICT(key) DO UPDATE SET value=excluded.value,
                                             updated_at=excluded.updated_at""",
            (key, str(value), now),
        )
    conn.commit()
    conn.close()


def _row_to_dict(row) -> dict:
    d = dict(row)
    if d.get("rule_details") and isinstance(d["rule_details"], str):
        d["rule_details"] = json.loads(d["rule_details"])
    return d
