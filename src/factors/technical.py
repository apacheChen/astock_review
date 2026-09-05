"""技术指标计算层：基于 MyTT 对每只候选股的日线批量计算指标快照"""
import numpy as np
import pandas as pd
from loguru import logger

try:
    from src.factors import MyTT as T
except Exception:
    from factors import MyTT as T


def _f(x):
    """安全转 float，NaN/Inf/异常返回 None"""
    try:
        v = float(x)
        return None if (np.isnan(v) or np.isinf(v)) else v
    except Exception:
        return None


def compute_indicators(df: pd.DataFrame, symbol: str = "") -> dict:
    """
    输入单只股票日线（需含 open/high/low/close/volume，按日期升序），
    返回最新一期指标快照 dict；数据不足或异常时返回尽量多的可用字段。
    """
    out = {"symbol": symbol}
    if df is None or len(df) < 5:
        return out
    try:
        c = df["close"].astype(float).reset_index(drop=True)
        h = df["high"].astype(float).reset_index(drop=True)
        l = df["low"].astype(float).reset_index(drop=True)
        v = df["volume"].astype(float).reset_index(drop=True)
        n = len(c)
        last = n - 1

        # ---- 均线与形态 ----
        ma5 = T.MA(c, 5)
        ma10 = T.MA(c, 10)
        ma20 = T.MA(c, 20)
        ma60 = T.MA(c, 60)
        out["close"] = _f(c.iloc[last])
        out["ma5"] = _f(ma5.iloc[last])
        out["ma10"] = _f(ma10.iloc[last])
        out["ma20"] = _f(ma20.iloc[last])
        out["ma60"] = _f(ma60.iloc[last])
        out["ma_bull"] = bool(
            out["ma5"] and out["ma10"] and out["ma20"]
            and out["ma5"] > out["ma10"] > out["ma20"])
        out["above_ma20"] = bool(out["ma20"] and out["close"] > out["ma20"])
        out["above_ma60"] = bool(out["ma60"] and out["close"] > out["ma60"])

        # ---- MACD ----
        dif, dea, bar = T.MACD(c)
        out["dif"] = _f(dif.iloc[last])
        out["dea"] = _f(dea.iloc[last])
        out["macd_bar"] = _f(bar.iloc[last])
        try:
            out["macd_golden_recent"] = bool(T.EXIST(T.CROSS(dif, dea), 3).iloc[last])
            b_last, b_prev = _f(bar.iloc[last]), _f(bar.iloc[last - 1])
            out["macd_bar_increasing"] = bool(
                b_last is not None and b_prev is not None
                and b_last > b_prev > 0)
        except Exception:
            pass

        # ---- KDJ ----
        k, d, j = T.KDJ(h, l, c)
        out["kdj_k"] = _f(k.iloc[last])
        out["kdj_d"] = _f(d.iloc[last])
        out["kdj_j"] = _f(j.iloc[last])
        try:
            out["kdj_golden_recent"] = bool(T.EXIST(T.CROSS(k, d), 3).iloc[last])
        except Exception:
            pass

        # ---- RSI ----
        out["rsi6"] = _f(T.RSI(c, 6).iloc[last])
        out["rsi14"] = _f(T.RSI(c, 14).iloc[last])

        # ---- BOLL 位置（0=下轨 1=上轨）----
        bmid, bup, blw = T.BOLL(c)
        bu, bl = _f(bup.iloc[last]), _f(blw.iloc[last])
        if bu is not None and bl is not None and bu > bl:
            out["boll_pos"] = (out["close"] - bl) / (bu - bl)

        # ---- 量能 ----
        vma5 = T.MA(v, 5)
        vr5 = _f(v.iloc[last] / vma5.iloc[last]) if _f(vma5.iloc[last]) else None
        out["vol_ratio_ma5"] = vr5
        out["volume_surge"] = bool(vr5 and vr5 >= 1.5)
        if n >= 3:
            out["vol_shrink"] = bool(v.iloc[last] < v.iloc[last - 1] < v.iloc[last - 2])

        # ---- 60 日高低点位置（0=最低 1=最高）----
        if n >= 60:
            hh = _f(T.HHV(h, 60).iloc[last])
            ll = _f(T.LLV(l, 60).iloc[last])
        else:
            hh = _f(h.max())
            ll = _f(l.min())
        if hh is not None and ll is not None and hh > ll:
            out["pos_60d"] = (out["close"] - ll) / (hh - ll)
            out["near_60d_high"] = bool(out["pos_60d"] >= 0.85)

        # ---- 波动 ----
        atr14 = _f(T.ATR(h, l, c, 14).iloc[last])
        out["atr14"] = atr14
        if atr14 and out["close"]:
            out["atr_pct"] = atr14 / out["close"] * 100

        # ---- 连涨 / 涨停统计 ----
        out["up_days_3"] = int((c.diff() > 0).iloc[max(0, last - 2):last + 1].sum())
        if "pct_chg" in df.columns:
            pc = df["pct_chg"].astype(float).reset_index(drop=True)
            out["pct_today"] = _f(pc.iloc[last])
            if n >= 60:
                out["limit_up_cnt_60d"] = int((pc.iloc[-60:] >= 9.7).sum())
        if "turnover" in df.columns:
            to = df["turnover"].astype(float).reset_index(drop=True)
            out["turnover"] = _f(to.iloc[last])
    except Exception as e:
        logger.warning(f"指标计算异常 {symbol}: {e}")
    return out


def batch_compute(daily_map: dict) -> dict:
    """批量计算：{symbol: 日线DataFrame} -> {symbol: 指标快照dict}"""
    result = {}
    for sym, df in (daily_map or {}).items():
        try:
            result[sym] = compute_indicators(df, sym)
        except Exception as e:
            logger.warning(f"batch_compute {sym} 失败: {e}")
    return result
