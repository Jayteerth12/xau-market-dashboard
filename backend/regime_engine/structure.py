"""
Module: Market Structure — HH/HL vs LH/LL sequencing.
Labels the sequence of the last two swing highs and last two swing lows.
"""
import pandas as pd


def _find_swing_highs(series: pd.Series, window: int = 5, min_prominence_pct: float = 0.001) -> list:
    """Swing high at index i: series[i] is the max in [i-window, i+window]."""
    swings = []
    for i in range(window, len(series) - window):
        val = series.iloc[i]
        if val != series.iloc[i - window: i + window + 1].max():
            continue
        surrounding_low = min(series.iloc[i - window: i].min(), series.iloc[i + 1: i + window + 1].min())
        if (val - surrounding_low) / val >= min_prominence_pct:
            swings.append({'idx': i, 'price': float(val)})
    return swings


def _find_swing_lows(series: pd.Series, window: int = 5, min_prominence_pct: float = 0.001) -> list:
    """Swing low at index i: series[i] is the min in [i-window, i+window]."""
    swings = []
    for i in range(window, len(series) - window):
        val = series.iloc[i]
        if val != series.iloc[i - window: i + window + 1].min():
            continue
        surrounding_high = max(series.iloc[i - window: i].max(), series.iloc[i + 1: i + window + 1].max())
        if (surrounding_high - val) / surrounding_high >= min_prominence_pct:
            swings.append({'idx': i, 'price': float(val)})
    return swings


def classify_structure(df: pd.DataFrame, window: int = 5) -> dict:
    """Label market structure from the last two swing highs/lows."""
    highs = _find_swing_highs(df['high'], window=window)
    lows = _find_swing_lows(df['low'], window=window)

    rising_highs = len(highs) >= 2 and highs[-1]['price'] > highs[-2]['price']
    falling_highs = len(highs) >= 2 and highs[-1]['price'] < highs[-2]['price']
    rising_lows = len(lows) >= 2 and lows[-1]['price'] > lows[-2]['price']
    falling_lows = len(lows) >= 2 and lows[-1]['price'] < lows[-2]['price']

    if rising_highs and rising_lows:
        label = 'HH/HL'
    elif falling_highs and falling_lows:
        label = 'LH/LL'
    else:
        label = 'Mixed/Range'

    return {
        'structure_label': label,
        'structure_last_swing_high': highs[-1]['price'] if highs else None,
        'structure_last_swing_low': lows[-1]['price'] if lows else None,
    }
