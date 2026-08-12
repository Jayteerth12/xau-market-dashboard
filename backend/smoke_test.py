"""
One runnable check for the whole pipeline: fetches live XAUUSD data and
asserts every stage produces sane output. Needs OANDA_TOKEN in the
environment (or backend/.env).

Run: python smoke_test.py
"""
from regime_engine.data_loader import get_candles, get_live_price
from regime_engine.market_state import compute_market_state
from regime_engine.detector import detect_regime
from regime_engine.structure import classify_structure
from regime_engine.levels import get_liquidity_features, get_session_context
from regime_engine.setup_matching import score_setups, tradeability_verdict, SETUPS

df = get_candles("XAUUSD", "1h", 300)
assert len(df) >= 250, f"expected 250+ bars, got {len(df)}"

market_state = compute_market_state(df)
assert market_state["state_label"] in {
    "Strong Trend Expansion", "Trending", "Neutral", "Compression",
    "Reversing / Unstable", "Choppy", "High Choppiness / Low Edge",
}, market_state
assert 0 <= market_state["state_score"] <= 100, market_state

regime = detect_regime(df)
assert regime["regime"] in {"STRONG_BULL", "WEAK_BULL", "RANGING", "WEAK_BEAR", "STRONG_BEAR", "HIGH_VOL"}, regime

structure = classify_structure(df)
assert structure["structure_label"] in {"HH/HL", "LH/LL", "Mixed/Range"}, structure

liquidity = get_liquidity_features(df)
session_context = get_session_context(df)
assert session_context["current_session"] in {"ASIAN", "LONDON", "NY", "OVERLAP", "OFF"}, session_context

setups = score_setups(market_state, structure, session_context)
assert {s["setup"] for s in setups["ranked"]} == set(SETUPS)

verdict = tradeability_verdict(market_state["state_score"])
assert verdict in {"Favorable", "Selective", "Low Edge", "Avoid"}, verdict

price = get_live_price("XAUUSD")
assert price > 0

print("smoke test OK:")
print(f'  XAUUSD ${price:,.2f}  ·  "{market_state["state_label"]}" ({market_state["state_score"]}/100)  ·  {verdict}')
print(f'  regime={regime["regime"]}  structure={structure["structure_label"]}  session={session_context["current_session"]}')
print(f'  top setup: {setups["ranked"][0]["setup"]} ({setups["ranked"][0]["score"]}/5)')
