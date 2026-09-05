"""Baostock 副源：能连则做交叉验证（招1），连不上自动跳过不影响主流程"""
import pandas as pd
from loguru import logger


def _mkt(symbol: str) -> str:
    """根据代码判断市场前缀"""
    if symbol.startswith(("6", "9")):
        return "sh"
    if symbol.startswith(("4", "8")):
        return "bj"
    return "sz"


def fetch_daily(symbol: str, start: str, end: str) -> pd.DataFrame:
    """拉日线数据（前复权）。任何异常都返回空表，不抛错不阻塞主流程"""
    try:
        import baostock as bs
    except Exception as e:
        logger.warning(f"baostock 未安装或不可用: {e}")
        return pd.DataFrame()

    try:
        lg = bs.login()
        if lg.error_code != "0":
            logger.warning(f"baostock 登录失败: {lg.error_msg}")
            return pd.DataFrame()
        try:
            rs = bs.query_history_k_data_plus(
                code=f"{_mkt(symbol)}.{symbol}",
                fields="date,open,high,low,close,preclose,volume,amount,turn,pctChg,isST",
                start_date=start, end_date=end,
                frequency="d", adjustflag="2")
            rows = []
            while rs.error_code == "0" and rs.next():
                rows.append(rs.get_row_data())
        finally:
            bs.logout()

        if not rows:
            return pd.DataFrame()

        df = pd.DataFrame(rows, columns=rs.fields)
        for c in df.columns:
            if c != "date":
                df[c] = pd.to_numeric(df[c], errors="coerce")
        df["date"] = pd.to_datetime(df["date"])
        df["symbol"] = symbol
        df = df.rename(columns={"turn": "turnover", "pctChg": "pct_chg"})
        return df[["symbol", "date", "open", "high", "low", "close",
                   "preclose", "volume", "amount", "turnover", "pct_chg"]]
    except Exception as e:
        logger.warning(f"BS 副源拉取失败 {symbol}: {e}")
        return pd.DataFrame()
