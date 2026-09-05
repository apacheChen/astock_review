"""SQLite 存储层:复盘结果持久化 + 自选股管理。纯标准库 sqlite3,零外部依赖"""
import sqlite3
import math
import pandas as pd
from loguru import logger
from pathlib import Path
from datetime import datetime


# ============ 数据目录(兼容 PC 与 Android) ============

def _db_dir() -> Path:
    """按优先级找一个可写目录,失败自动降级"""
    candidates = [
        Path.cwd() / "data",
        Path.home() / ".astock_review",
        Path("/tmp") / "astock_review",
    ]
    for d in candidates:
        try:
            d.mkdir(parents=True, exist_ok=True)
            test = d / ".write_test"
            test.touch()
            test.unlink()
            return d
        except Exception:
            continue
    import tempfile
    d = Path(tempfile.gettempdir()) / "astock_review"
    d.mkdir(parents=True, exist_ok=True)
    return d


DB_PATH = _db_dir() / "review.db"

_conn = None


def get_conn() -> sqlite3.Connection:
    """获取(并初始化)数据库连接"""
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _init_tables(_conn)
        logger.info(f"数据库就绪: {DB_PATH}")
    return _conn


def _init_tables(conn: sqlite3.Connection):
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS runs (
        run_id     TEXT PRIMARY KEY,
        run_time   TEXT NOT NULL,
        n_snapshot INTEGER,
        n_l1       INTEGER,
        n_l2       INTEGER,
        n_final    INTEGER,
        elapsed    REAL,
        status     TEXT DEFAULT 'ok',
        error      TEXT
    );
    CREATE TABLE IF NOT EXISTS reviews (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id    TEXT NOT NULL,
        run_time  TEXT NOT NULL,
        symbol    TEXT NOT NULL,
        name      TEXT,
        price     REAL,
        pct_chg   REAL,
        score     REAL,
        stars     INTEGER,
        tags      TEXT,
        reasons   TEXT,
        turnover  REAL,
        vol_ratio REAL,
        float_mv  REAL,
        verify_bs_diff  REAL,
        verify_tdx_diff REAL
    );
    CREATE INDEX IF NOT EXISTS idx_reviews_symbol ON reviews(symbol);
    CREATE INDEX IF NOT EXISTS idx_reviews_run ON reviews(run_id);
    CREATE TABLE IF NOT EXISTS watchlist (
        symbol      TEXT PRIMARY KEY,
        name        TEXT,
        note        TEXT,
        added_time  TEXT NOT NULL
    );
    """)
    conn.commit()


def _num(v):
    """转可入库数值,None/NaN/Inf -> None"""
    try:
        f = float(v)
        return None if (math.isnan(f) or math.isinf(f)) else f
    except Exception:
        return None


# ============ 复盘运行记录 ============

def save_run(run_id: str, n_snapshot: int = 0, n_l1: int = 0,
             n_l2: int = 0, n_final: int = 0, elapsed: float = 0.0,
             status: str = "ok", error: str = "") -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        get_conn().execute(
            "INSERT OR REPLACE INTO runs VALUES (?,?,?,?,?,?,?,?,?)",
            (run_id, now, n_snapshot, n_l1, n_l2, n_final, elapsed,
             status, error))
        get_conn().commit()
    except Exception as e:
        logger.warning(f"save_run 失败: {e}")


def list_runs(limit: int = 30) -> pd.DataFrame:
    """最近 N 次复盘运行记录"""
    try:
        rows = get_conn().execute(
            "SELECT * FROM runs ORDER BY run_time DESC LIMIT ?",
            (limit,)).fetchall()
        return pd.DataFrame([dict(r) for r in rows])
    except Exception as e:
        logger.warning(f"list_runs 失败: {e}")
        return pd.DataFrame()


def latest_run_id():
    """最近一次成功复盘的 run_id"""
    try:
        row = get_conn().execute(
            "SELECT run_id FROM runs WHERE status='ok'"
            " ORDER BY run_time DESC LIMIT 1").fetchone()
        return row["run_id"] if row else None
    except Exception:
        return None


# ============ 复盘结果 ============

def save_review_results(run_id: str, df: pd.DataFrame) -> int:
    """保存一次复盘的候选股结果,返回写入条数"""
    if df is None or df.empty:
        return 0
    run_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rows = []
    for _, r in df.iterrows():
        rows.append((
            run_id, run_time,
            str(r.get("symbol", "")),
            str(r.get("name", "") or ""),
            _num(r.get("price")), _num(r.get("pct_chg")),
            _num(r.get("score")), _num(r.get("stars")),
            str(r.get("tags", "") or ""), str(r.get("reasons", "") or ""),
            _num(r.get("turnover")), _num(r.get("vol_ratio")),
            _num(r.get("float_mv")),
            _num(r.get("verify_bs_diff")), _num(r.get("verify_tdx_diff")),
        ))
    try:
        conn = get_conn()
        conn.executemany(
            "INSERT INTO reviews (run_id, run_time, symbol, name, price,"
            " pct_chg, score, stars, tags, reasons, turnover, vol_ratio,"
            " float_mv, verify_bs_diff, verify_tdx_diff)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
        conn.commit()
        logger.info(f"已保存 {len(rows)} 条复盘结果 (run={run_id})")
        return len(rows)
    except Exception as e:
        logger.warning(f"save_review_results 失败: {e}")
        return 0


def get_run_results(run_id: str) -> pd.DataFrame:
    """某次复盘的候选股列表,按分数降序"""
    try:
        rows = get_conn().execute(
            "SELECT * FROM reviews WHERE run_id=? ORDER BY score DESC",
            (run_id,)).fetchall()
        return pd.DataFrame([dict(r) for r in rows])
    except Exception as e:
        logger.warning(f"get_run_results 失败: {e}")
        return pd.DataFrame()


def load_latest_results() -> pd.DataFrame:
    """加载最近一次成功复盘的结果(App 启动时恢复显示)"""
    rid = latest_run_id()
    return get_run_results(rid) if rid else pd.DataFrame()


def symbol_history(symbol: str, limit: int = 30) -> pd.DataFrame:
    """单只股票的历史复盘记录(分数变化轨迹)"""
    try:
        rows = get_conn().execute(
            "SELECT run_time, score, stars, price, pct_chg, tags"
            " FROM reviews WHERE symbol=? ORDER BY run_time DESC LIMIT ?",
            (symbol, limit)).fetchall()
        return pd.DataFrame([dict(r) for r in rows])
    except Exception as e:
        logger.warning(f"symbol_history 失败: {e}")
        return pd.DataFrame()


# ============ 自选股 ============

def add_watch(symbol: str, name: str = "", note: str = "") -> bool:
    try:
        get_conn().execute(
            "INSERT OR REPLACE INTO watchlist VALUES (?,?,?,?)",
            (symbol, name, note,
             datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        get_conn().commit()
        return True
    except Exception as e:
        logger.warning(f"add_watch 失败: {e}")
        return False


def remove_watch(symbol: str) -> bool:
    try:
        get_conn().execute("DELETE FROM watchlist WHERE symbol=?", (symbol,))
        get_conn().commit()
        return True
    except Exception as e:
        logger.warning(f"remove_watch 失败: {e}")
        return False


def list_watch() -> pd.DataFrame:
    try:
        rows = get_conn().execute(
            "SELECT * FROM watchlist ORDER BY added_time DESC").fetchall()
        return pd.DataFrame([dict(r) for r in rows])
    except Exception as e:
        logger.warning(f"list_watch 失败: {e}")
        return pd.DataFrame()


def is_watched(symbol: str) -> bool:
    try:
        row = get_conn().execute(
            "SELECT 1 FROM watchlist WHERE symbol=?", (symbol,)).fetchone()
        return row is not None
    except Exception:
        return False
