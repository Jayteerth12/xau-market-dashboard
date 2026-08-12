"""
Liquidity Level Analysis & Session Context
Session highs/lows/opens/closes (Asian, London, NY), previous day H/L/C,
equal highs/lows, round-number proximity, and dynamic session context
(whatever session is active now + whatever session most recently completed).
"""
import pandas as pd
import numpy as np


# Session windows in UTC hours
SESSIONS = {
    'asian':   ( 0,  9),
    'london':  ( 7, 16),
    'ny':      (13, 21),
    'overlap': (13, 16),
}


def _round_px(value: float) -> float:
    """Round with precision scaled to price magnitude: 2dp for ~$20+ instruments
    (XAUUSD, indices), 5dp for sub-$20 instruments (most FX pairs) — a fixed
    2dp everywhere silently destroys FX precision (1.15xxx -> 1.15)."""
    return round(value, 2 if abs(value) >= 20 else 5)


def _get_session_levels(df: pd.DataFrame, session: str, single_day: bool = False) -> dict:
    """
    Extract OHLC for a named session.
    single_day=True: strictly the single most recent calendar day that has a
    matching bar (used by get_session_context). single_day=False: most recent
    30 matching bars, which can span >1 day on wide intraday session windows
    (used by get_liquidity_features's broader liquidity-level scan).
    """
    start_h, end_h = SESSIONS[session]

    if not isinstance(df.index, pd.DatetimeIndex):
        return {f'{session}_high': 0.0, f'{session}_low': 0.0,
                f'{session}_open': 0.0, f'{session}_close': 0.0}

    mask = (df.index.hour >= start_h) & (df.index.hour < end_h)
    matching = df[mask]

    if matching.empty:
        return {f'{session}_high': 0.0, f'{session}_low': 0.0,
                f'{session}_open': 0.0, f'{session}_close': 0.0}

    if single_day:
        last_day = matching.index.normalize()[-1]
        recent_session = matching[matching.index.normalize() == last_day]
    else:
        recent_session = matching.tail(30)

    return {
        f'{session}_high':  _round_px(float(recent_session['high'].max())),
        f'{session}_low':   _round_px(float(recent_session['low'].min())),
        f'{session}_open':  _round_px(float(recent_session['open'].iloc[0])),
        f'{session}_close': _round_px(float(recent_session['close'].iloc[-1])),
    }


def _session_ohlc_stats(o: float, h: float, l: float, c: float) -> dict:
    """Range/body/wick/efficiency breakdown for one completed session."""
    rng = h - l
    if rng <= 0:
        return {'range': 0.0, 'body': 0.0, 'body_pct': 0.0, 'upper_wick_pct': 0.0,
                'lower_wick_pct': 0.0, 'direction': 'Neutral', 'efficiency': 0.0}
    body = abs(c - o)
    upper_wick = h - max(o, c)
    lower_wick = min(o, c) - l
    direction = 'Bullish' if c > o else 'Bearish' if c < o else 'Neutral'
    return {
        'range':          _round_px(rng),
        'body':           _round_px(body),
        'body_pct':       round(body / rng * 100, 1),
        'upper_wick_pct': round(upper_wick / rng * 100, 1),
        'lower_wick_pct': round(lower_wick / rng * 100, 1),
        'direction':      direction,
        'efficiency':     round(body / rng, 3),
    }


def get_session_context(df: pd.DataFrame, as_of=None) -> dict:
    """
    Dynamic session context: whichever session is currently active, plus
    whichever session most recently *completed*, with full OHLC stats for
    both. No hardcoded "Asian strategy"/"London strategy" branching — just
    "what's the most recent completed session right now."
    """
    if not isinstance(df.index, pd.DatetimeIndex) or df.empty:
        return {'current_session': 'OFF', 'previous_session': None}

    import datetime
    now_hour = as_of.hour if as_of is not None else datetime.datetime.now(datetime.timezone.utc).hour
    order = ['asian', 'london', 'ny']  # overlap is a sub-window of london/ny, not a distinct slot here

    current = None
    for name in order:
        start_h, end_h = SESSIONS[name]
        if start_h <= now_hour < end_h:
            current = name
            break

    completed_today = [n for n in order if SESSIONS[n][1] <= now_hour]
    previous = completed_today[-1] if completed_today else order[-1]  # before Asian opens -> prior day's NY

    levels = _get_session_levels(df, previous, single_day=True)
    o, h, l, c = (levels[f'{previous}_open'], levels[f'{previous}_high'],
                  levels[f'{previous}_low'], levels[f'{previous}_close'])
    prev_stats = _session_ohlc_stats(o, h, l, c) if h else _session_ohlc_stats(0, 0, 0, 0)

    price = float(df['close'].iloc[-1])

    cur_levels = _get_session_levels(df, current, single_day=True) if current else \
        {f'current_high': 0.0, f'current_low': 0.0, f'current_open': 0.0, f'current_close': 0.0}
    if current:
        cur_h, cur_l, cur_o = cur_levels[f'{current}_high'], cur_levels[f'{current}_low'], cur_levels[f'{current}_open']
    else:
        cur_h = cur_l = cur_o = 0.0

    return {
        'current_session':  current.upper() if current else 'OFF',
        'previous_session': previous.upper(),
        'previous_session_open':  o,
        'previous_session_high':  h,
        'previous_session_low':   l,
        'previous_session_close': c,
        'previous_session_stats': prev_stats,
        'current_session_open':   cur_o,
        'current_session_high':   cur_h,
        'current_session_low':    cur_l,
        'current_session_range':  _round_px(cur_h - cur_l) if cur_h else 0.0,
        'current_session_return_pct': round((price - cur_o) / cur_o * 100, 2) if cur_o else 0.0,
        'distance_from_prev_high': _round_px(price - h) if h else 0.0,
        'distance_from_prev_low':  _round_px(price - l) if l else 0.0,
        'price_vs_prev_close_pct': round((price - c) / c * 100, 2) if c else 0.0,
    }


def _get_previous_day_levels(df: pd.DataFrame) -> dict:
    """Extract PDH (Previous Day High), PDL (Previous Day Low), PDC (Previous Day Close)."""
    if not isinstance(df.index, pd.DatetimeIndex):
        return {'pdh': 0.0, 'pdl': 0.0, 'pdc': 0.0}

    daily = df.resample('D').agg({
        'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'
    }).dropna()

    if len(daily) < 2:
        return {'pdh': 0.0, 'pdl': 0.0, 'pdc': 0.0}

    prev = daily.iloc[-2]
    return {
        'pdh': round(float(prev['high']),  2),
        'pdl': round(float(prev['low']),   2),
        'pdc': round(float(prev['close']), 2),
    }


def _find_equal_levels(series: pd.Series,
                        tolerance_pct: float = 0.001,
                        lookback: int = 50,
                        min_touches: int = 2) -> list:
    """Price levels where the series has multiple touches within tolerance —
    potential liquidity pools. Returns list of (level, count) tuples."""
    recent = series.tail(lookback)
    levels = []

    sorted_vals = sorted(recent.values)
    i = 0
    while i < len(sorted_vals):
        val = sorted_vals[i]
        cluster = [v for v in sorted_vals if abs(v - val) / val <= tolerance_pct]
        if len(cluster) >= min_touches:
            level = float(np.mean(cluster))
            if not any(abs(level - existing[0]) / level < tolerance_pct * 3
                       for existing in levels):
                levels.append((round(level, 2), len(cluster)))
            i += len(cluster)
        else:
            i += 1

    return levels


def get_liquidity_features(df: pd.DataFrame, as_of=None) -> dict:
    """Compute all liquidity reference levels and return as a feature dict."""
    price = float(df['close'].iloc[-1])
    hl  = df['high'] - df['low']
    hpc = (df['high'] - df['close'].shift(1)).abs()
    lpc = (df['low']  - df['close'].shift(1)).abs()
    atr = float(pd.concat([hl, hpc, lpc], axis=1).max(axis=1).rolling(14).mean().iloc[-1])
    thr = atr * 0.3

    features = {'atr': round(atr, 2)}

    for session in ['asian', 'london', 'ny', 'overlap']:
        features.update(_get_session_levels(df, session))

    features.update(_get_previous_day_levels(df))

    pdh = features.get('pdh', 0)
    pdl = features.get('pdl', 0)
    features['above_pdh']    = bool(pdh > 0 and price > pdh)
    features['below_pdl']    = bool(pdl > 0 and price < pdl)
    features['near_pdh']     = bool(pdh > 0 and abs(price - pdh) < thr)
    features['near_pdl']     = bool(pdl > 0 and abs(price - pdl) < thr)

    eq_highs = _find_equal_levels(df['high'].tail(100))
    features['equal_highs_level'] = eq_highs[0][0] if eq_highs else 0.0
    features['near_equal_highs']  = bool(eq_highs and abs(price - eq_highs[0][0]) < thr)

    eq_lows = _find_equal_levels(df['low'].tail(100))
    features['equal_lows_level'] = eq_lows[0][0] if eq_lows else 0.0
    features['near_equal_lows']  = bool(eq_lows and abs(price - eq_lows[0][0]) < thr)

    # Round number proximity — gold-scale default; a coarse heuristic for any symbol.
    nearest_round = round(price / 50) * 50
    features['nearest_round_number'] = float(nearest_round)
    features['near_round_number']    = bool(abs(price - nearest_round) < thr)

    a_high = features.get('asian_high', 0)
    a_low  = features.get('asian_low', 0)
    features['asian_range']       = round(float(a_high - a_low), 2) if a_high else 0.0
    features['above_asian_high']  = bool(a_high > 0 and price > a_high)
    features['below_asian_low']   = bool(a_low  > 0 and price < a_low)

    import datetime
    utc_hour = as_of.hour if as_of is not None else datetime.datetime.now(datetime.timezone.utc).hour
    if 13 <= utc_hour < 16:
        session = 'OVERLAP'
    elif 7 <= utc_hour < 16:
        session = 'LONDON'
    elif 13 <= utc_hour < 21:
        session = 'NY'
    elif 0 <= utc_hour < 9:
        session = 'ASIAN'
    else:
        session = 'OFF'

    features['current_session']       = session
    features['is_london_session']      = bool(session in ('LONDON', 'OVERLAP'))
    features['is_ny_session']          = bool(session in ('NY', 'OVERLAP'))
    features['is_london_ny_overlap']   = bool(session == 'OVERLAP')
    features['is_high_activity']       = bool(session in ('LONDON', 'NY', 'OVERLAP'))

    return features
