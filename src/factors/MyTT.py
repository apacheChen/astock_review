"""MyTT 技术指标库：pandas/numpy 向量化实现，接口对齐通达信公式习惯"""
import numpy as np
import pandas as pd


# ============ 基础序列工具 ============

def _s(x):
    """转 pandas Series"""
    if isinstance(x, pd.Series):
        return x.astype(float)
    return pd.Series(np.asarray(x, dtype=float))


def MA(x, n):
    """简单移动平均"""
    return _s(x).rolling(n, min_periods=1).mean()


def EMA(x, n):
    """指数移动平均"""
    return _s(x).ewm(span=n, min_periods=1, adjust=False).mean()


def SMA_CN(x, n, m):
    """中国式 SMA：y = (x*m + y'*(n-m)) / n"""
    return _s(x).ewm(alpha=m / n, adjust=False).mean()


def WMA(x, n):
    """加权移动平均（权重 1..n）"""
    w = np.arange(1, n + 1, dtype=float)
    return _s(x).rolling(n).apply(lambda a: np.dot(a, w) / w.sum(), raw=True)


def REF(x, n):
    """n 期前的值"""
    return _s(x).shift(n)


def DIFF(x, n=1):
    """一阶差分"""
    return _s(x).diff(n)


def STD(x, n):
    """n 期标准差（总体标准差，对齐通达信）"""
    return _s(x).rolling(n, min_periods=1).std(ddof=0)


def SUM(x, n):
    """n 期累计和，n=0 表示从头累计"""
    s = _s(x)
    if n == 0:
        return s.cumsum()
    return s.rolling(n, min_periods=1).sum()


def HHV(x, n):
    """n 期最高值"""
    return _s(x).rolling(n, min_periods=1).max()


def LLV(x, n):
    """n 期最低值"""
    return _s(x).rolling(n, min_periods=1).min()


def AVEDEV(x, n):
    """n 期平均绝对偏差"""
    return _s(x).rolling(n, min_periods=1).apply(
        lambda a: np.abs(a - a.mean()).mean(), raw=True)


# ============ 信号判断工具 ============

def CROSS(a, b):
    """a 上穿 b"""
    a, b = _s(a), _s(b)
    return (a > b) & (a.shift(1) <= b.shift(1))


def EVERY(cond, n):
    """连续 n 期都成立"""
    return _s(cond.astype(float)).rolling(n, min_periods=1).sum() == n


def EXIST(cond, n):
    """近 n 期存在成立"""
    return _s(cond.astype(float)).rolling(n, min_periods=1).sum() > 0


def COUNT(cond, n):
    """近 n 期成立的次数"""
    return _s(cond.astype(float)).rolling(n, min_periods=1).sum()


def BARSLAST(cond):
    """上一次条件成立到当前的周期数（从未成立返回 NaN）"""
    c = _s(cond.astype(float)).values
    out = np.full(len(c), np.nan)
    last = -1
    for i, v in enumerate(c):
        if v:
            last = i
        if last >= 0:
            out[i] = i - last
    return pd.Series(out)


# ============ 常用技术指标 ============

def MACD(close, fast=12, slow=26, signal=9):
    """返回 (DIF, DEA, MACD柱)（柱=（DIF-DEA）*2，对齐国内软件）"""
    dif = EMA(close, fast) - EMA(close, slow)
    dea = EMA(dif, signal)
    bar = (dif - dea) * 2
    return dif, dea, bar


def KDJ(high, low, close, n=9, m1=3, m2=3):
    """返回 (K, D, J)"""
    h = HHV(high, n)
    l = LLV(low, n)
    rng = (h - l).replace(0, np.nan)
    rsv = ((close - l) / rng * 100).fillna(50.0)
    k = SMA_CN(rsv, m1, 1)
    d = SMA_CN(k, m2, 1)
    j = 3 * k - 2 * d
    return k, d, j


def RSI(close, n=14):
    """相对强弱指标（中国式 SMA 平滑，全涨=100）"""
    chg = _s(close).diff()
    up = chg.clip(lower=0)
    dn = (-chg).clip(lower=0)
    up_avg = SMA_CN(up, n, 1)
    dn_avg = SMA_CN(dn, n, 1)
    dn_avg = dn_avg.replace(0, np.nan)
    rs = up_avg / dn_avg
    return (100 - 100 / (1 + rs)).fillna(100.0)


def BOLL(close, n=20, k=2):
    """布林带，返回 (中轨, 上轨, 下轨)"""
    mid = MA(close, n)
    sd = STD(close, n)
    return mid, mid + k * sd, mid - k * sd


def TR(high, low, close):
    """真实波幅（首根用 high-low 补齐）"""
    pc = _s(close).shift(1)
    tr = pd.concat([
        _s(high) - _s(low),
        (_s(high) - pc).abs(),
        (_s(low) - pc).abs(),
    ], axis=1).max(axis=1)
    if len(tr) and np.isnan(tr.iloc[0]):
        tr.iloc[0] = float(_s(high).iloc[0]) - float(_s(low).iloc[0])
    return tr


def ATR(high, low, close, n=14):
    """平均真实波幅"""
    return MA(TR(high, low, close), n)


def CCI(high, low, close, n=14):
    """顺势指标"""
    tp = (_s(high) + _s(low) + _s(close)) / 3
    md = AVEDEV(tp, n).replace(0, np.nan)
    return (tp - MA(tp, n)) / (0.015 * md)


def WR(high, low, close, n=14):
    """威廉指标（中国式：数值大=弱）"""
    h = HHV(high, n)
    l = LLV(low, n)
    rng = (h - l).replace(0, np.nan)
    return (h - _s(close)) / rng * 100


def BIAS(close, n=6):
    """乖离率"""
    ma = MA(close, n)
    return (_s(close) - ma) / ma * 100


def ROC(close, n=12):
    """变动率"""
    ref = REF(close, n).replace(0, np.nan)
    return (_s(close) - ref) / ref * 100


def MTM(close, n=12):
    """动量"""
    return _s(close) - REF(close, n)


def DPO(close, n=20):
    """区间震荡线"""
    return _s(close) - REF(MA(close, n), n // 2 + 1)


def PSY(close, n=12):
    """心理线：近 n 期上涨天数占比"""
    up = (_s(close).diff() > 0).astype(float)
    return COUNT(up, n) / n * 100


def MFI(high, low, close, volume, n=14):
    """资金流量指标"""
    tp = (_s(high) + _s(low) + _s(close)) / 3
    mf = tp * _s(volume)
    chg = tp.diff()
    pos = mf.where(chg > 0, 0.0).rolling(n, min_periods=1).sum()
    neg = mf.where(chg < 0, 0.0).rolling(n, min_periods=1).sum()
    neg = neg.replace(0, np.nan)
    return (100 - 100 / (1 + pos / neg)).fillna(100.0)


def OBV(close, volume):
    """能量潮"""
    direction = np.sign(_s(close).diff()).fillna(0.0)
    return (direction * _s(volume)).cumsum()


def VR(close, volume, n=26):
    """成交量比率"""
    chg = _s(close).diff()
    av = _s(volume).where(chg > 0, 0.0).rolling(n, min_periods=1).sum()
    bv = _s(volume).where(chg < 0, 0.0).rolling(n, min_periods=1).sum()
    cv = _s(volume).where(chg == 0, 0.0).rolling(n, min_periods=1).sum()
    denom = (bv + cv / 2).replace(0, np.nan)
    return ((av + cv / 2) / denom * 100).fillna(100.0)
