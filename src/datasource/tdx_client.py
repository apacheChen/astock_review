"""通达信第三源：在线分钟线聚合成日线，做交叉验证。不可用自动跳过"""
import pandas as pd
from loguru import logger

_client = None


def get_client():
    """懒加载通达信连接，失败返回 None，不抛错"""
    global _client
    if _client is None:
        try:
            from mootdx.quotes import Quotes
            _client = Quotes.factory(market="std", bestip=True)
        except Exception as e:
            logger.warning(f"mootdx 不可用: {e}")
            return None
    return _client


def fetch_daily_from_minutes(symbol: str, days: int = 60) -> pd.DataFrame:
    """拉 60 分钟线并聚合成日线，用于与东财日线交叉验证"""
    client = get_client()
    if client is None:
        return pd.DataFrame()
    try:
        df = client.bars(symbol=symbol, frequency=3, offset=days * 4)
        if df is None or df.empty:
            return pd.DataFrame()
        df = df.reset_index()
        df["date"] = pd.to_datetime(df["datetime"]).dt.normalize()
        agg = df.groupby("date").agg(
            open=("open", "first"),
            high=("high", "max"),
            low=("low", "min"),
            close=("close", "last"),
            volume=("volume", "sum"),
            amount=("amount", "sum"),
        ).reset_index()
        agg["symbol"] = symbol
        return agg
    except Exception as e:
        logger.warning(f"TDX 拉取失败 {symbol}: {e}")
        return pd.DataFrame()
