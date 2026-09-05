"""五维打分:趋势30+动量25+量能20+RSI10+安全15=100分,输出分数/星级/标签/理由"""
import pandas as pd
from loguru import logger

WEIGHTS = {"trend": 30, "momentum": 25, "volume": 20, "rsi": 10, "safety": 15}


def _b(v):
    """安全转 bool"""
    return bool(v) if v is not None else False


def _f(v):
    """安全转 float"""
    try:
        return float(v)
    except Exception:
        return None


def score_row(r: dict) -> dict:
    """对单只股票打分,返回 score/stars/tags/reasons"""
    reasons, tags = [], []
    score = 0.0

    # ---- 趋势 30 ----
    t = 0.0
    if _b(r.get("ma_bull")):
        t += 12
        reasons.append("均线多头(5>10>20)")
        tags.append("多头排列")
    if _b(r.get("above_ma20")):
        t += 8
        reasons.append("站上20日线")
    if _b(r.get("above_ma60")):
        t += 5
        reasons.append("站上60日线")
    pos = _f(r.get("pos_60d"))
    if pos is not None:
        if pos >= 0.85:
            t += 5
            tags.append("近60日新高区")
        elif pos >= 0.5:
            t += 3
    score += min(t, WEIGHTS["trend"])

    # ---- 动量 25 ----
    m = 0.0
    if _b(r.get("macd_golden_recent")):
        m += 10
        tags.append("MACD金叉")
    if _b(r.get("macd_bar_increasing")):
        m += 8
        reasons.append("MACD红柱放大")
    if _b(r.get("kdj_golden_recent")):
        m += 7
        tags.append("KDJ金叉")
    ud = int(r.get("up_days_3") or 0)
    if ud == 3:
        m += 5
        tags.append("三连阳")
    elif ud == 2:
        m += 3
    score += min(m, WEIGHTS["momentum"])

    # ---- 量能 20 ----
    v = 0.0
    if _b(r.get("volume_surge")):
        v += 10
        tags.append("放量")
    vr = _f(r.get("vol_ratio_ma5"))
    if vr is not None:
        if 1.2 <= vr <= 3.0:
            v += 6
            reasons.append(f"量为5日均量{vr:.1f}倍")
        elif vr > 5:
            v += 2
            tags.append("异常放量")
    if _b(r.get("vol_shrink")):
        v += 4
        reasons.append("量能温和收缩")
    score += min(v, WEIGHTS["volume"])

    # ---- RSI 10 ----
    rs = 0.0
    rsi6 = _f(r.get("rsi6"))
    rsi14 = _f(r.get("rsi14"))
    if rsi14 is not None:
        if 45 <= rsi14 <= 70:
            rs += 6
            reasons.append(f"RSI14={rsi14:.0f}强势区")
        elif 70 < rsi14 <= 80:
            rs += 3
            tags.append("RSI偏高")
        elif rsi14 > 80:
            tags.append("RSI超买")
        else:
            rs += 2
    if rsi6 is not None and rsi14 is not None and rsi6 > rsi14:
        rs += 4
    score += min(rs, WEIGHTS["rsi"])

    # ---- 安全 15 ----
    s = WEIGHTS["safety"] * 0.5
    atr_pct = _f(r.get("atr_pct"))
    if atr_pct is not None:
        if atr_pct <= 3:
            s += 5
        elif atr_pct <= 5:
            s += 3
        else:
            s -= 3
            tags.append("高波动")
            reasons.append(f"日波动{atr_pct:.1f}%偏大")
    bp = _f(r.get("boll_pos"))
    if bp is not None:
        if bp >= 0.98:
            s -= 5
            reasons.append("触及布林上轨")
        elif 0.3 <= bp <= 0.8:
            s += 3
    lu = int(r.get("limit_up_cnt_60d") or 0)
    if lu >= 3:
        s -= 4
        tags.append("近期多涨停(妖股风险)")
    pct_today = _f(r.get("pct_today"))
    if pct_today is not None and pct_today >= 7:
        s -= 3
        reasons.append(f"今日已涨{pct_today:.1f}%追高风险")
    score += max(0.0, min(s, WEIGHTS["safety"]))

    # ---- 汇总 ----
    score = max(0.0, min(100.0, score))
    stars = 1 + int(score // 20)
    if score >= 80:
        tags.insert(0, "强烈关注")
    elif score >= 65:
        tags.insert(0, "关注")
    return {"score": round(score, 1), "stars": stars,
            "tags": "|".join(tags[:6]), "reasons": "; ".join(reasons[:6])}


def rank(df: pd.DataFrame) -> pd.DataFrame:
    """对漏斗输出整体打分排序,新增 score/stars/tags/reasons 列"""
    if df is None or df.empty:
        return pd.DataFrame()
    out = df.copy().reset_index(drop=True)
    scores = []
    for _, row in out.iterrows():
        try:
            scores.append(score_row(row.to_dict()))
        except Exception as e:
            logger.warning(f"打分异常 {row.get('symbol')}: {e}")
            scores.append({"score": 0.0, "stars": 1, "tags": "", "reasons": ""})
    out = pd.concat([out, pd.DataFrame(scores)], axis=1)
    return out.sort_values("score", ascending=False).reset_index(drop=True)
