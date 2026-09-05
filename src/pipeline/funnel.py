"""三层漏斗主逻辑:L1 快照常识过滤 -> L2 技术面粗筛 -> L3 日线+指标精筛
附带招1交叉验证(多源收盘价对比)与招4除权校验(复权口径一致性)"""
import time
import numpy as np
import pandas as pd
from loguru import logger

try:
    from src.datasource import em_client, bs_client, tdx_client
    from src.pipeline.common_sense import (
        filter_snapshot, daily_common_sense_check
    )
    from src.factors.technical import compute_indicators
except Exception:
    from datasource import em_client, bs_client, tdx_client
    from pipeline.common_sense import (
        filter_snapshot, daily_common_sense_check
    )
    from factors.technical import compute_indicators


# ============ 日期工具 ============

def _today() -> str:
    return pd.Timestamp.now().strftime("%Y-%m-%d")


def _days_ago(n: int) -> str:
    return (pd.Timestamp.now() - pd.Timedelta(days=n)).strftime("%Y-%m-%d")


# ============ L2 技术面粗筛(纯快照字段,零网络请求) ============

def coarse_filter(df: pd.DataFrame) -> pd.DataFrame:
    """
    用快照字段快速粗筛,把几千只压缩到 ~200 只:
    - 成交额 >= 1 亿(流动性门槛)
    - 换手率 1% ~ 15%(过冷没人玩,过热主力出货)
    - 量比 0.8 ~ 5(温和或显著放量)
    - 涨幅 -2% ~ 7%(避开暴跌与追高)
    - 价格 3 ~ 300 元
    - 流通市值 30 ~ 800 亿(中小盘主导)
    热度 = 成交额(亿) × 量比,降序取前 N
    """
    if df is None or df.empty:
        return pd.DataFrame()
    d = df.copy()
    con = d["amount"].fillna(0) >= 1e8
    if "turnover" in d.columns:
        con &= d["turnover"].fillna(0).between(1.0, 15.0)
    if "vol_ratio" in d.columns:
        con &= d["vol_ratio"].fillna(0).between(0.8, 5.0)
    if "pct_chg" in d.columns:
        con &= d["pct_chg"].fillna(0).between(-2.0, 7.0)
    if "price" in d.columns:
        con &= d["price"].fillna(0).between(3.0, 300.0)
    if "float_mv" in d.columns:
        con &= d["float_mv"].fillna(0).between(3e9, 8e10)
    d = d[con]
    if d.empty:
        return d
    d["heat"] = (d["amount"].fillna(0) / 1e8) * d["vol_ratio"].fillna(1.0)
    return d.sort_values("heat", ascending=False)


# ============ 招4 除权校验 ============

def exright_check(symbol: str, snap_pct, lookback_days: int = 120) -> bool:
    """
    前复权日线的最新涨跌幅应与快照涨跌幅基本一致(容差 1%)
    偏差过大说明数据口径混乱(除权日未同步/复权错误),剔除
    数据不足或接口异常时不判死,避免误杀
    """
    try:
        if snap_pct is None or pd.isna(snap_pct):
            return True
        df_qfq = em_client.fetch_daily(symbol, _days_ago(lookback_days),
                                       _today(), fqt=1)
        if df_qfq.empty or len(df_qfq) < 2:
            return True
        pct_qfq = float(df_qfq["pct_chg"].iloc[-1])
        if pd.isna(pct_qfq):
            return True
        return abs(pct_qfq - float(snap_pct)) <= 1.0
    except Exception as e:
        logger.warning(f"除权校验异常 {symbol}: {e}")
        return True


# ============ 招1 交叉验证 ============

def cross_verify(symbol: str, em_close: float) -> dict:
    """
    用 Baostock / 通达信 副源拉最近收盘价,与东财对比
    任一副源偏差 > 0.5% 就判异常
    """
    result = {"pass": True, "bs_close": None, "tdx_close": None,
              "bs_diff": None, "tdx_diff": None}
    try:
        bs_df = bs_client.fetch_daily(symbol, _days_ago(10), _today())
        if bs_df is not None and not bs_df.empty:
            bs_close = float(bs_df["close"].iloc[-1])
            result["bs_close"] = bs_close
            if em_close and em_close > 0:
                diff = abs(bs_close - em_close) / em_close * 100
                result["bs_diff"] = round(diff, 3)
                if diff > 0.5:
                    result["pass"] = False
    except Exception as e:
        logger.debug(f"BS 验证跳过 {symbol}: {e}")
    try:
        tdx_df = tdx_client.fetch_daily_from_minutes(symbol, days=10)
        if tdx_df is not None and not tdx_df.empty:
            tdx_close = float(tdx_df["close"].iloc[-1])
            result["tdx_close"] = tdx_close
            if em_close and em_close > 0:
                diff = abs(tdx_close - em_close) / em_close * 100
                result["tdx_diff"] = round(diff, 3)
                if diff > 0.5:
                    result["pass"] = False
    except Exception as e:
        logger.debug(f"TDX 验证跳过 {symbol}: {e}")
    return result


# ============ 主入口:三层漏斗 ============

def run_funnel(snapshot: pd.DataFrame,
               n_l2: int = 200,
               n_final: int = 30,
               daily_days: int = 120) -> pd.DataFrame:
    """
    三层漏斗主入口
    snapshot: em_client.fetch_market_snapshot() 的输出
    返回: DataFrame,每行一只候选股,带快照字段 + 常识标记 + 指标 + 验证结果
    """
    t0 = time.time()
    logger.info(f"=== 漏斗启动: 快照 {len(snapshot) if snapshot is not None else 0} 只 ===")

    # ---- L1 常识过滤(剔 ST/停牌/仙股/一字) ----
    l1 = filter_snapshot(snapshot)
    logger.info(f"L1 常识过滤后: {len(l1)} 只 ({time.time()-t0:.1f}s)")
    if l1.empty:
        return pd.DataFrame()

    # ---- L2 技术面粗筛 ----
    l2 = coarse_filter(l1).head(n_l2)
    logger.info(f"L2 粗筛后: {len(l2)} 只 ({time.time()-t0:.1f}s)")
    if l2.empty:
        return pd.DataFrame()

    # ---- L3 拉日线 + 指标 + 常识校验 + 除权校验 ----
    start = _days_ago(int(daily_days * 1.6))
    end = _today()
    rows = []
    for i, (_, row) in enumerate(l2.iterrows(), 1):
        sym = row["symbol"]
        try:
            daily = em_client.fetch_daily(sym, start, end, fqt=1)
            if daily is None or daily.empty:
                continue
            flags = daily_common_sense_check(daily, sym)
            if not flags.get("buyable", False):
                continue
            if not exright_check(sym, row.get("pct_chg"), daily_days):
                logger.info(f"[除权异常] {sym} 剔除")
                continue
            ind = compute_indicators(daily, sym)
            rec = {**row.to_dict(), **flags, **ind}
            rows.append(rec)
        except Exception as e:
            logger.warning(f"L3 处理 {sym} 失败: {e}")
        if i % 20 == 0:
            logger.info(f"L3 进度 {i}/{len(l2)} ({time.time()-t0:.1f}s)")

    l3 = pd.DataFrame(rows)
    logger.info(f"L3 精筛后: {len(l3)} 只 ({time.time()-t0:.1f}s)")
    if l3.empty:
        return l3

    # ---- 招1 交叉验证(只对前 n_final 只做,节省时间) ----
    if "heat" in l3.columns:
        l3 = l3.sort_values("heat", ascending=False)
    verified = []
    for _, row in l3.head(n_final).iterrows():
        sym = row["symbol"]
        em_close = float(row.get("close") or 0)
        v = cross_verify(sym, em_close)
        if not v["pass"]:
            logger.info(
                f"[交叉验证失败] {sym} em={em_close} "
                f"bs={v['bs_close']} tdx={v['tdx_close']}")
            continue
        rec = {**row.to_dict()}
        for k, vv in v.items():
            rec[f"verify_{k}"] = vv
        verified.append(rec)

    out = pd.DataFrame(verified)
    logger.info(f"=== 漏斗完成: {len(out)} 只候选 ({time.time()-t0:.1f}s) ===")
    return out
