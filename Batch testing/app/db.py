"""SQLite 持久化层（线程安全，使用全局连接 + 锁）。"""
import json
import sqlite3
import threading
from datetime import datetime, timezone

from .config import DB_PATH

_lock = threading.RLock()
_conn = None


def now_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def init() -> None:
    get_conn()


def get_conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _init_schema(_conn)
    return _conn

def _init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT,
            started_at TEXT,
            finished_at TEXT,
            config_json TEXT,
            stats_json TEXT
        );
        CREATE TABLE IF NOT EXISTS test_cases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER NOT NULL,
            ref_id TEXT,
            scenario TEXT,
            difficulty TEXT,
            conversation_json TEXT,
            expected_output TEXT,
            sort_order INTEGER
        );
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER NOT NULL,
            test_case_id INTEGER NOT NULL,
            ref_id TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            attempt_count INTEGER DEFAULT 0,
            error TEXT,
            actual_output TEXT,
            turns_json TEXT,
            ttft_ms REAL,
            latency_ms REAL,
            input_tokens INTEGER,
            output_tokens INTEGER,
            total_tokens INTEGER,
            judge_json TEXT,
            scores_json TEXT,
            total_score REAL,
            confidence REAL,
            passed INTEGER,
            is_badcase INTEGER,
            human_reviewed INTEGER DEFAULT 0,
            human_pass INTEGER,
            human_score REAL,
            human_scores_json TEXT,
            human_note TEXT,
            updated_at TEXT
        );
        CREATE TABLE IF NOT EXISTS run_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER NOT NULL,
            seq INTEGER NOT NULL,
            level TEXT,
            message TEXT,
            ts TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_results_run ON results(run_id);
        CREATE INDEX IF NOT EXISTS idx_logs_run_seq ON run_logs(run_id, seq);
        """
    )
    conn.commit()

def execute(sql: str, params=()):
    with _lock:
        conn = get_conn()
        cur = conn.execute(sql, params)
        conn.commit()
        return cur


def executemany(sql: str, seq) -> None:
    with _lock:
        conn = get_conn()
        conn.executemany(sql, seq)
        conn.commit()


def query(sql: str, params=()):
    with _lock:
        conn = get_conn()
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def query_one(sql: str, params=()):
    with _lock:
        conn = get_conn()
        row = conn.execute(sql, params).fetchone()
        return dict(row) if row else None


# ---------------- Runs ----------------
def create_run(name: str, config: dict) -> int:
    cur = execute(
        "INSERT INTO runs(name, status, created_at, config_json) VALUES(?,?,?,?)",
        (name, "pending", now_str(), json.dumps(config, ensure_ascii=False)),
    )
    return cur.lastrowid


def update_run(run_id: int, **fields) -> None:
    if not fields:
        return
    cols = []
    vals = []
    for k, v in fields.items():
        cols.append(f"{k}=?")
        vals.append(v)
    vals.append(run_id)
    execute(f"UPDATE runs SET {', '.join(cols)} WHERE id=?", vals)


def get_run(run_id: int):
    return query_one("SELECT * FROM runs WHERE id=?", (run_id,))


def delete_run(run_id: int) -> None:
    with _lock:
        conn = get_conn()
        conn.execute("DELETE FROM run_logs WHERE run_id=?", (run_id,))
        conn.execute("DELETE FROM results WHERE run_id=?", (run_id,))
        conn.execute("DELETE FROM test_cases WHERE run_id=?", (run_id,))
        conn.execute("DELETE FROM runs WHERE id=?", (run_id,))
        conn.commit()


def list_runs():
    return query("SELECT * FROM runs ORDER BY id DESC")

# ---------------- Test cases ----------------
def add_test_cases(run_id: int, cases) -> None:
    rows = [
        (
            run_id, c["ref_id"], c["scenario"], c["difficulty"],
            json.dumps(c["conversation"], ensure_ascii=False),
            c["expected_output"], i,
        )
        for i, c in enumerate(cases)
    ]
    executemany(
        "INSERT INTO test_cases(run_id, ref_id, scenario, difficulty, "
        "conversation_json, expected_output, sort_order) VALUES(?,?,?,?,?,?,?)",
        rows,
    )


def create_results_for_run(run_id: int) -> None:
    execute(
        "INSERT INTO results(run_id, test_case_id, ref_id, status) "
        "SELECT ?, id, ref_id, 'pending' FROM test_cases WHERE run_id=? ORDER BY sort_order",
        (run_id, run_id),
    )


def get_test_cases(run_id: int):
    return query(
        """
        SELECT tc.id, tc.ref_id, tc.scenario, tc.difficulty,
               tc.conversation_json, tc.expected_output,
               r.id AS result_id, r.status AS result_status, r.attempt_count AS attempt_count
        FROM test_cases tc
        JOIN results r ON r.test_case_id = tc.id AND r.run_id = tc.run_id
        WHERE tc.run_id = ?
        ORDER BY tc.sort_order
        """,
        (run_id,),
    )


def get_results(run_id: int):
    return query(
        """
        SELECT r.*, tc.scenario, tc.difficulty, tc.conversation_json, tc.expected_output
        FROM results r
        JOIN test_cases tc ON tc.id = r.test_case_id
        WHERE r.run_id = ?
        ORDER BY tc.sort_order
        """,
        (run_id,),
    )


def get_result(result_id: int):
    return query_one("SELECT * FROM results WHERE id=?", (result_id,))


def update_result(result_id: int, **fields) -> None:
    fields = dict(fields)
    fields["updated_at"] = now_str()
    cols = []
    vals = []
    for k, v in fields.items():
        cols.append(f"{k}=?")
        vals.append(v)
    vals.append(result_id)
    execute(f"UPDATE results SET {', '.join(cols)} WHERE id=?", vals)


def result_counts(run_id: int):
    return query_one(
        """
        SELECT COUNT(*) AS total,
               COALESCE(SUM(CASE WHEN status='success' THEN 1 ELSE 0 END), 0) AS success,
               COALESCE(SUM(CASE WHEN status='failed' THEN 1 ELSE 0 END), 0) AS failed,
               COALESCE(SUM(CASE WHEN status='running' THEN 1 ELSE 0 END), 0) AS running,
               COALESCE(SUM(CASE WHEN status='pending' THEN 1 ELSE 0 END), 0) AS pending
        FROM results WHERE run_id = ?
        """,
        (run_id,),
    )

# ---------------- Logs ----------------
def add_log(run_id: int, level: str, message: str) -> None:
    execute(
        "INSERT INTO run_logs(run_id, seq, level, message, ts) "
        "SELECT ?, COALESCE(MAX(seq), 0) + 1, ?, ?, ? FROM run_logs WHERE run_id = ?",
        (run_id, level, message, now_str(), run_id),
    )


def get_logs(run_id: int, after_seq: int = 0):
    return query(
        "SELECT seq, level, message, ts FROM run_logs WHERE run_id = ? AND seq > ? ORDER BY seq",
        (run_id, after_seq),
    )


def last_log_seq(run_id: int) -> int:
    row = query_one("SELECT COALESCE(MAX(seq), 0) AS m FROM run_logs WHERE run_id = ?", (run_id,))
    return row["m"] if row else 0




