"""
Module: Kinematics — velocity, acceleration, trend quality, expansion.
Physics-style metrics that lose less information than bounded oscillators
(RSI/Stoch compress magnitude away; these don't).

  velocity_score    ATR(fast) / ATR(slow)              — is volatility speeding up?
  expansion_score   TrueRange / avg(TrueRange, n)       — is THIS candle unusual?
  efficiency_ratio  net distance / path length          — Kaufman's ER, "Trend Quality"
  choppiness_index  Dreiss choppiness, 0-100            — inverse of trend quality
  velocity/accel    1st/2nd derivative of smoothed close, ATR-normalised

Returns named features for the unified feature matrix (prefix: kin_).
"""
import pandas as pd
import numpy as np


def _true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    hl  = high - low
    hpc = (high - close.shift(1)).abs()
    lpc = (low  - close.shift(1)).abs()
    return pd.concat([hl, hpc, lpc], axis=1).max(axis=1)


def velocity_score(high: pd.Series, low: pd.Series, close: pd.Series,
                    fast: int = 14, slow: int = 100) -> pd.Series:
    """ATR(fast) / ATR(slow). >1 = market moving faster than its own recent norm."""
    tr = _true_range(high, low, close)
    atr_fast = tr.rolling(fast).mean()
    atr_slow = tr.rolling(slow).mean()
    return (atr_fast / atr_slow.replace(0, np.nan)).fillna(1.0)


def expansion_score(high: pd.Series, low: pd.Series, close: pd.Series,
                     length: int = 20) -> pd.Series:
    """Current candle's true range / n-bar average true range."""
    tr = _true_range(high, low, close)
    avg_tr = tr.rolling(length).mean()
    return (tr / avg_tr.replace(0, np.nan)).fillna(1.0)


def efficiency_ratio(close: pd.Series, length: int = 10) -> pd.Series:
    """
    Kaufman's Efficiency Ratio — 'Trend Quality'.
    net distance travelled / total path zig-zagged, over `length` bars.
    1.0 = perfectly straight move, ~0 = pure noise.
    """
    net_move = (close - close.shift(length)).abs()
    path     = close.diff().abs().rolling(length).sum()
    return (net_move / path.replace(0, np.nan)).fillna(0.0).clip(0, 1)


def choppiness_index(high: pd.Series, low: pd.Series, close: pd.Series,
                      length: int = 14) -> pd.Series:
    """Dreiss Choppiness Index, 0-100. High = choppy/rangebound, low = trending."""
    tr = _true_range(high, low, close)
    atr_sum   = tr.rolling(length).sum()
    hi_lo_rng = high.rolling(length).max() - low.rolling(length).min()
    ci = 100 * np.log10(atr_sum / hi_lo_rng.replace(0, np.nan)) / np.log10(length)
    return ci.clip(0, 100).fillna(50.0)


def momentum_kinematics(close: pd.Series, high: pd.Series, low: pd.Series,
                         smooth: int = 5, atr_length: int = 14) -> tuple[pd.Series, pd.Series]:
    """
    First and second derivative of price, smoothed to cut noise, normalised
    by ATR so acceleration is comparable across symbols/timeframes.
    Returns (velocity, acceleration) — both in ATR units per bar.
    """
    smoothed = close.ewm(span=smooth, adjust=False).mean()
    atr = _true_range(high, low, close).rolling(atr_length).mean().replace(0, np.nan)
    velocity = (smoothed.diff() / atr).fillna(0.0)
    acceleration = velocity.diff().fillna(0.0)
    return velocity, acceleration


def compute_kinematics(df: pd.DataFrame) -> pd.DataFrame:
    """Add all kinematics columns to a copy of the OHLC DataFrame."""
    d = df.copy()
    h, l, c = d['high'], d['low'], d['close']

    d['kin_velocity_score']   = velocity_score(h, l, c)
    d['kin_expansion_score']  = expansion_score(h, l, c)
    d['kin_trend_quality']    = efficiency_ratio(c)
    d['kin_choppiness']       = choppiness_index(h, l, c)
    vel, acc = momentum_kinematics(c, h, l)
    d['kin_momentum_velocity']     = vel
    d['kin_momentum_acceleration'] = acc
    return d
