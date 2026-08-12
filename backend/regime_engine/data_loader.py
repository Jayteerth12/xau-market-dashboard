"""
Live market data — OANDA v20 REST API only.
Trimmed from the main trading stack's data_loader.py: no Kaggle/historical
data, no local DB. This service is live-only.
"""
import time
import pandas as pd
import oandapyV20
import oandapyV20.endpoints.instruments as instruments
import oandapyV20.endpoints.pricing as pricing
from oandapyV20.exceptions import V20Error

from config import OANDA_TOKEN, OANDA_ACCOUNT_ID, OANDA_ENVIRONMENT

GRANULARITY = {"1m": "M1", "5m": "M5", "15m": "M15", "1h": "H1", "4h": "H4", "1d": "D"}
SYMBOLS     = {"XAUUSD": "XAU_USD", "XAGUSD": "XAG_USD"}


def _oanda_instrument(symbol: str) -> str:
    """Convert friendly symbol names to OANDA instrument format."""
    s = symbol.upper()
    if s in SYMBOLS:
        return SYMBOLS[s]
    if len(s) == 6 and "_" not in s:
        return f"{s[:3]}_{s[3:]}"  # EURUSD -> EUR_USD
    return s  # already in OANDA format or unknown


def get_candles(symbol: str, timeframe: str, count: int = 300) -> pd.DataFrame:
    """
    Fetch OHLCV candles from OANDA.
    Returns pd.DataFrame  columns: open, high, low, close, volume
                          index:   UTC DatetimeIndex
    """
    client = oandapyV20.API(access_token=OANDA_TOKEN, environment=OANDA_ENVIRONMENT)
    params = {
        "count":       count,
        "granularity": GRANULARITY.get(timeframe.lower(), "H1"),
        "price":       "M",
    }
    for attempt in range(3):
        try:
            r = instruments.InstrumentsCandles(_oanda_instrument(symbol), params=params)
            client.request(r)
            break
        except V20Error as e:
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)  # 1s, 2s

    rows = [
        {
            "time":   pd.to_datetime(c["time"]),
            "open":   float(c["mid"]["o"]),
            "high":   float(c["mid"]["h"]),
            "low":    float(c["mid"]["l"]),
            "close":  float(c["mid"]["c"]),
            "volume": int(c["volume"]),
        }
        for c in r.response["candles"] if c["complete"]
    ]

    df = pd.DataFrame(rows).set_index("time")
    df.index = df.index.tz_convert("UTC")
    return df


def get_live_price(symbol: str) -> float:
    """Return the current mid price (bid+ask / 2) from OANDA's pricing stream."""
    client = oandapyV20.API(access_token=OANDA_TOKEN, environment=OANDA_ENVIRONMENT)
    r = pricing.PricingInfo(
        accountID=OANDA_ACCOUNT_ID,
        params={"instruments": _oanda_instrument(symbol)},
    )
    client.request(r)
    p = r.response["prices"][0]
    return (float(p["bids"][0]["price"]) + float(p["asks"][0]["price"])) / 2
