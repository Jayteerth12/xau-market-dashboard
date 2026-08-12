"""
Setup Compatibility Engine.
Maps the market-state label produced by market_state.classify_state() onto
a 0-5 fit score per trading-setup type. Does not predict direction — only
says which setup *styles* suit the current environment.
"""

SETUPS = [
    'Trend Following',
    'Trend Pullback',
    'Breakout',
    'Breakout Retest',
    'Mean Reversion',
    'Liquidity Sweep',
    'Compression Expansion',
    'Opening Range Breakout',
]

# state_label -> {setup: score 0-5}. Rows match the exact labels emitted by
# market_state.classify_state().
_MATRIX = {
    'Strong Trend Expansion': {
        'Trend Following': 5, 'Trend Pullback': 5, 'Breakout': 4, 'Breakout Retest': 5,
        'Mean Reversion': 0, 'Liquidity Sweep': 2, 'Compression Expansion': 1, 'Opening Range Breakout': 3,
    },
    'Trending': {
        'Trend Following': 4, 'Trend Pullback': 4, 'Breakout': 3, 'Breakout Retest': 4,
        'Mean Reversion': 1, 'Liquidity Sweep': 2, 'Compression Expansion': 1, 'Opening Range Breakout': 2,
    },
    'Compression': {
        'Trend Following': 0, 'Trend Pullback': 1, 'Breakout': 4, 'Breakout Retest': 3,
        'Mean Reversion': 2, 'Liquidity Sweep': 2, 'Compression Expansion': 5, 'Opening Range Breakout': 3,
    },
    'Neutral': {
        'Trend Following': 1, 'Trend Pullback': 1, 'Breakout': 2, 'Breakout Retest': 2,
        'Mean Reversion': 3, 'Liquidity Sweep': 3, 'Compression Expansion': 2, 'Opening Range Breakout': 2,
    },
    'Reversing / Unstable': {
        'Trend Following': 0, 'Trend Pullback': 1, 'Breakout': 1, 'Breakout Retest': 2,
        'Mean Reversion': 3, 'Liquidity Sweep': 4, 'Compression Expansion': 2, 'Opening Range Breakout': 1,
    },
    'Choppy': {
        'Trend Following': 0, 'Trend Pullback': 0, 'Breakout': 0, 'Breakout Retest': 1,
        'Mean Reversion': 2, 'Liquidity Sweep': 1, 'Compression Expansion': 1, 'Opening Range Breakout': 0,
    },
    'High Choppiness / Low Edge': {
        'Trend Following': 0, 'Trend Pullback': 0, 'Breakout': 0, 'Breakout Retest': 0,
        'Mean Reversion': 1, 'Liquidity Sweep': 0, 'Compression Expansion': 0, 'Opening Range Breakout': 0,
    },
}

TRADEABILITY_THRESHOLDS = [(80, 'Favorable'), (65, 'Selective'), (50, 'Low Edge'), (0, 'Avoid')]


def tradeability_verdict(state_score: float) -> str:
    for threshold, verdict in TRADEABILITY_THRESHOLDS:
        if state_score >= threshold:
            return verdict
    return 'Avoid'


def _within_orb_window(session_context: dict) -> bool:
    cur_range = session_context.get('current_session_range', 0)
    # No completed bars/range means the session just opened.
    return cur_range == 0


def score_setups(market_state: dict, structure: dict | None = None,
                  session_context: dict | None = None, selected: list[str] | None = None) -> dict:
    """Rank setups for the current state_label. `selected` restricts to the
    trader's enabled setups; None scores all of them."""
    row = _MATRIX.get(market_state.get('state_label'), _MATRIX['Neutral'])
    structure = structure or {}
    session_context = session_context or {}

    bull_lean = market_state.get('state_label') in ('Strong Trend Expansion', 'Trending') and \
        structure.get('structure_label') == 'HH/HL'
    bear_lean = market_state.get('state_label') in ('Strong Trend Expansion', 'Trending') and \
        structure.get('structure_label') == 'LH/LL'
    structure_agrees = bull_lean or bear_lean
    structure_conflicts = market_state.get('state_label') in ('Strong Trend Expansion', 'Trending') and \
        structure.get('structure_label') == 'Mixed/Range'

    names = selected if selected else SETUPS
    ranked = []
    for name in names:
        if name not in row:
            continue
        score = row[name]
        if name in ('Trend Following', 'Trend Pullback'):
            if structure_agrees:
                score += 1
            elif structure_conflicts:
                score -= 1
        if name == 'Opening Range Breakout':
            in_orb_window = session_context.get('current_session_open') and \
                _within_orb_window(session_context)
            if not in_orb_window:
                score = 0
        score = max(0, min(5, score))
        ranked.append({'setup': name, 'score': score, 'stars': '⭐' * score + '☆' * (5 - score)})

    ranked.sort(key=lambda r: r['score'], reverse=True)
    return {
        'ranked': ranked,
        'preferred': [r['setup'] for r in ranked if r['score'] >= 4],
        'avoid': [r['setup'] for r in ranked if r['score'] <= 1],
    }
