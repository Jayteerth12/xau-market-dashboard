"""
Module: Market State Classifier
Combines kinematics (velocity/expansion/trend-quality/choppiness) with the
ADX regime detector into one 0-100 tradability score and a state label.
Answers "is this market worth trading at all?" before direction is even
considered.
"""
import pandas as pd

from regime_engine.kinematics import compute_kinematics
from regime_engine.detector import detect_regime

# Score weights — must sum to 1.0
_WEIGHTS = {
    'trend_quality': 0.35,   # efficiency ratio, 0-1 -> 0-100
    'anti_chop':     0.25,   # 100 - choppiness index
    'expansion':     0.20,   # expansion_score centred on 1.0
    'velocity':      0.20,   # velocity_score centred on 1.0
}


def _center_ratio_score(ratio: float, low: float = 0.5, high: float = 2.5) -> float:
    """Map a ratio centred at 1.0 to a 0-100 'is something happening' score.
    Values far from 1.0 in either direction (dead market vs blowoff) score low;
    a moderate expansion (1.2-1.8x normal) scores highest."""
    if ratio <= low or ratio >= high:
        return 20.0
    peak = 1.6  # sweet spot: clearly moving, not yet a blowoff
    dist = abs(ratio - peak) / (high - low)
    return max(20.0, 100.0 - dist * 160.0)


def classify_state(score: float, kin_last: pd.Series, regime: dict) -> str:
    """Label overrides based on structure, not just the blended score."""
    if kin_last['kin_expansion_score'] > 1.3 and kin_last['kin_velocity_score'] > 1.2 \
            and kin_last['kin_trend_quality'] > 0.45:
        return 'Strong Trend Expansion'
    if kin_last['kin_choppiness'] > 61.8 or kin_last['kin_trend_quality'] < 0.25:
        return 'High Choppiness / Low Edge'
    if regime.get('regime') == 'RANGING' and kin_last['kin_expansion_score'] < 0.8 \
            and kin_last['kin_velocity_score'] < 0.9:
        return 'Compression'
    if regime.get('is_high_vol') and kin_last['kin_trend_quality'] < 0.4:
        return 'Reversing / Unstable'
    if score >= 65:
        return 'Trending'
    if score >= 45:
        return 'Neutral'
    return 'Choppy'


def compute_market_state(df: pd.DataFrame) -> dict:
    """Full dashboard: sub-scores, composite score, and state label."""
    d = compute_kinematics(df)
    last = d.iloc[-1]
    regime = detect_regime(df)

    trend_quality_score = last['kin_trend_quality'] * 100
    anti_chop_score      = 100 - last['kin_choppiness']
    expansion_sub        = _center_ratio_score(last['kin_expansion_score'])
    velocity_sub         = _center_ratio_score(last['kin_velocity_score'])

    composite = (
        trend_quality_score * _WEIGHTS['trend_quality'] +
        anti_chop_score      * _WEIGHTS['anti_chop'] +
        expansion_sub         * _WEIGHTS['expansion'] +
        velocity_sub          * _WEIGHTS['velocity']
    )
    # Ranging/high-vol regime caps the score — a choppy market can't score "tradable"
    # just because one sub-metric spiked.
    if regime.get('is_ranging'):
        composite = min(composite, 55.0)

    label = classify_state(composite, last, regime)

    return {
        'state_score':            round(composite, 1),
        'state_label':             label,
        'state_trend_quality':    round(trend_quality_score, 1),
        'state_anti_chop':        round(anti_chop_score, 1),
        'state_expansion':        round(expansion_sub, 1),
        'state_velocity':         round(velocity_sub, 1),
        'state_tradable':          bool(composite >= 45 and label != 'High Choppiness / Low Edge'),
    }
