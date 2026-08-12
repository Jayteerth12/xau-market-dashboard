"""
Market Regime Detector
Classifies current market conditions into one of six regimes.
Uses ADX (trend strength), ATR percentile (volatility), and DI± (direction).

Regime states:
  STRONG_BULL  — ADX > 35, price above EMA50, +DI > -DI
  WEAK_BULL    — ADX 20-35, price above EMA21, +DI > -DI
  RANGING      — ADX < 20
  WEAK_BEAR    — ADX 20-35, price below EMA21, -DI > +DI
  STRONG_BEAR  — ADX > 35, price below EMA50, -DI > +DI
  HIGH_VOL     — ATR in top 90th percentile (news / event driven)
"""
import pandas as pd
import numpy as np
import pandas_ta_classic as ta

ADX_STRONG   = 35
ADX_WEAK     = 20
ATR_VOL_PCT  = 90     # ATR percentile that triggers HIGH_VOL regime
ATR_LOOKBACK = 100    # Rolling window for ATR percentile calculation


def detect_regime(df: pd.DataFrame) -> dict:
    """Classify the current market regime from OHLCV data."""
    close = df['close']
    high  = df['high']
    low   = df['low']

    adx_df = ta.adx(high, low, close, length=14)
    adx    = float(adx_df.iloc[-1, 0]) if adx_df is not None else 20.0
    di_p   = float(adx_df.iloc[-1, 1]) if adx_df is not None else 20.0
    di_m   = float(adx_df.iloc[-1, 2]) if adx_df is not None else 20.0

    ema21  = float(ta.ema(close, length=21).iloc[-1] or close.iloc[-1])
    ema50  = float(ta.ema(close, length=50).iloc[-1] or close.iloc[-1])
    price  = float(close.iloc[-1])

    atr_series  = ta.atr(high, low, close, length=14).dropna()
    atr_current = float(atr_series.iloc[-1]) if len(atr_series) > 0 else 0.0
    atr_lookback = atr_series.tail(ATR_LOOKBACK)
    atr_pct      = float(
        (atr_current > atr_lookback).sum() / len(atr_lookback) * 100
    ) if len(atr_lookback) > 0 else 50.0

    is_high_vol = atr_pct >= ATR_VOL_PCT

    bull_di = di_p > di_m
    above_ema21 = price > ema21
    above_ema50 = price > ema50

    if is_high_vol:
        regime = 'HIGH_VOL'
    elif adx >= ADX_STRONG and bull_di and above_ema50:
        regime = 'STRONG_BULL'
    elif adx >= ADX_STRONG and not bull_di and not above_ema50:
        regime = 'STRONG_BEAR'
    elif ADX_WEAK <= adx < ADX_STRONG and bull_di and above_ema21:
        regime = 'WEAK_BULL'
    elif ADX_WEAK <= adx < ADX_STRONG and not bull_di and not above_ema21:
        regime = 'WEAK_BEAR'
    else:
        regime = 'RANGING'

    trend_regimes  = {'STRONG_BULL', 'WEAK_BULL', 'STRONG_BEAR', 'WEAK_BEAR'}
    bull_regimes   = {'STRONG_BULL', 'WEAK_BULL'}
    bear_regimes   = {'STRONG_BEAR', 'WEAK_BEAR'}

    return {
        'regime':            regime,
        'regime_adx':        round(adx, 1),
        'regime_di_p':       round(di_p, 1),
        'regime_di_m':       round(di_m, 1),
        'regime_atr_pct':    round(atr_pct, 1),
        'is_trending':       bool(regime in trend_regimes),
        'is_ranging':        bool(regime == 'RANGING'),
        'is_high_vol':       bool(is_high_vol),
        'is_bull_regime':    bool(regime in bull_regimes),
        'is_bear_regime':    bool(regime in bear_regimes),
        'regime_strong':     bool(adx >= ADX_STRONG),
        'regime_weak':       bool(ADX_WEAK <= adx < ADX_STRONG),
        'atr_current':       round(atr_current, 2),
    }
