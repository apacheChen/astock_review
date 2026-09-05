"""招3 常识校验：淘汰明显不能买/不该买的票，为漏斗减负"""
import pandas as pd
from loguru import logger


# ---------- 涨跌停幅度 ----------
def limit_pct(symbol: str) -> float:
    """按代码段返回涨跌停幅度：创业/科创 20%，北交 30%，主板 10%"""
    if symbol.startswith(("300", "301", "688", "689")):
        return 0.20
    if symbol.startswith(("8", "4")):
        return 0.30
    return 0.10


def is_limit_up(price, preclose, symbol: str, tol: float = 0.002) -> bool:
    """是否涨停（留 0.2% 容差，防四舍五入误判）"""
    try:
        if pd.isna(price) or pd.isna(preclose) or preclose <= 0:
            return False
        return float(price) >= float(preclose) * (1 + limit_pct(symbol) - tol)
    except Exception:
        return False


def is_limit_down(price, preclose, symbol: str, tol: float = 0.002) -> bool:
    """是否跌停"""
    try:
        if pd.isna(price) or pd.isna(preclose) or preclose <= 0:
            return False
        return float(price) <= float(preclose) * (1 - limit_pct(symbol) + tol)
    except Exception:
        return False


# ---------- 第一层：快照常识过滤 ----------
def filter_snapshot(snap: pd.DataFrame, keep_st: bool = False,
                    min_price: float = 2.0) -> pd.DataFrame:
    """
    快照级常识过滤：
    1) 剔除 ST / *ST / 退市股
    2) 剔除停牌（价格为空或零成交）
    3) 剔除仙股（价格 < min_price）
    4) 剔除疑似一字/秒板（触板且换手 < 0.2%，基本买不进）
    """
    if snap is None or snap.empty:
        return pd.DataFrame()
    df = snap.copy()
    n0 = len(df)

    # 1) ST / 退市
    if not keep_st and "is_st" in df.columns:
        df = df[~df["is_st"].fillna(False)]
    if "name" in df.columns:
        df = df[~df["name"].astype(str).str.contains("退", na=False)]

    # 2) 停牌 / 无效价
    if "price" in df.columns:
        df = df[df["price"].notna() & (df["price"] > 0)]
    if "amount" in df.columns:
        df = df[df["amount"].fillna(0) > 0]

    # 3) 仙股
    if "price" in df.columns:
        df = df[df["price"] >= min_price]

    # 4) 疑似一字/秒板：涨幅触板但几乎无换手
    if {"price", "pct_chg", "turnover", "symbol"} <= set(df.columns):
        def _sealed(row) -> bool:
            if pd.isna(row["pct_chg"]) or pd.isna(row["price"]) or row["price"] <= 0:
                return False
            preclose = row["price"] / (1 + row["pct_chg"] / 100)
            if is_limit_up(row["price"], preclose, row["symbol"]):
                return row["turnover"] is not None and pd.notna(row["turnover"]) \
                    and row["turnover"] < 0.2
            return False
        df = df[~df.apply(_sealed, axis=1)]

    logger.info(f"常识过滤: {n0} -> {len(df)}")
    return df


# ---------- 第三层：个股日线常识 ----------
def daily_common_sense_check(df_daily: pd.DataFrame, symbol: str,
                             min_history: int = 60) -> dict:
    """
    个股日线常识检查，返回标记字典：
    is_new        历史K线不足（次新股）
    is_one_word   一字板（买不进）
    is_t_board    T字板（极难买，只标记不强剔）
    limit_up_now  最新收盘涨停
    suspended     停牌
    buyable       综合判断是否可买
    reason        原因说明
    """
    flags = {"symbol": symbol, "is_new": False, "is_one_word": False,
             "is_t_board": False, "limit_up_now": False, "suspended": False,
             "buyable": True, "reason": ""}

    if df_daily is None or df_daily.empty:
        flags.update(buyable=False, reason="无日线数据")
        return flags

    n = len(df_daily)
    last = df_daily.iloc[-1]

    # 次新股
    if n < min_history:
        flags.update(is_new=True, buyable=False, reason=f"次新股(仅{n}根K线)")

    # 停牌（最新一根零成交）
    if "volume" in df_daily.columns and pd.notna(last.get("volume")) \
            and float(last["volume"]) <= 0:
        flags.update(suspended=True, buyable=False, reason="停牌")
        return flags

    # 涨停 / 一字板 / T字板
    preclose = float(df_daily["close"].iloc[-2]) if n >= 2 else float(last["open"])
    lu = is_limit_up(last["close"], preclose, symbol)
    flags["limit_up_now"] = lu

    if lu:
        o, h = float(last["open"]), float(last["high"])
        l, c = float(last["low"]), float(last["close"])
        eps = max(c * 1e-4, 0.001)
        if abs(o - h) < eps and abs(h - l) < eps and abs(l - c) < eps:
            flags.update(is_one_word=True, buyable=False, reason="一字板买不进")
        elif abs(o - h) < eps and abs(o - c) < eps and l < o - 5 * eps:
            flags.update(is_t_board=True, reason="T字板极难买入(不强制剔除)")

    return flags
