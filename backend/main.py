"""
XAU Market Dashboard API — standalone, read-only market-regime backend.
Classifies the current market environment for any OANDA instrument and
scores trading-setup fit. Does not predict direction, place trades, or
store any data — a single stateless endpoint plus a health check.

Start locally: uvicorn main:app --reload
Deployed on Render (or similar): uvicorn main:app --host 0.0.0.0 --port $PORT
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from regime_engine.data_loader import get_candles, get_live_price
from regime_engine.market_state import compute_market_state
from regime_engine.detector import detect_regime
from regime_engine.structure import classify_structure
from regime_engine.levels import get_liquidity_features, get_session_context
from regime_engine.setup_matching import score_setups, tradeability_verdict, SETUPS

app = FastAPI(title="XAU Market Dashboard API", version="1.0")

# Public, read-only, no auth/secrets in the response — safe to allow any origin.
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["GET"], allow_headers=["*"],
)

_MIN_REGIME_BARS = 250  # EMA200/ADX/kinematics(slow=100) need this much lookback for a stable read


@app.get("/health")
def health():
    return {"status": "running"}


@app.get("/setups")
def list_setups():
    return {"setups": SETUPS}


@app.get("/regime/{symbol}")
def regime(symbol: str, timeframe: str = "1h", htf: str = "4h", setups: str = None):
    """Market state, session context, key levels, and setup compatibility for
    `symbol` — any OANDA instrument (XAUUSD, EURUSD, ...). Does not predict
    direction; classifies the environment and scores which setup styles fit it."""
    df = get_candles(symbol, timeframe, 300)
    df_htf = get_candles(symbol, htf, 300)
    if len(df) < _MIN_REGIME_BARS or len(df_htf) < _MIN_REGIME_BARS:
        raise HTTPException(400, f"Not enough {symbol} {timeframe}/{htf} data returned by OANDA "
                                  f"(got {len(df)}/{len(df_htf)} bars, need {_MIN_REGIME_BARS}+). "
                                  f"Check the symbol is a valid OANDA instrument.")

    market_state = compute_market_state(df)
    market_regime = detect_regime(df)
    structure = classify_structure(df)
    liquidity = get_liquidity_features(df)
    session_context = get_session_context(df)
    htf_market_state = compute_market_state(df_htf)

    selected = setups.split(",") if setups else None
    setup_scores = score_setups(market_state, structure, session_context, selected)

    try:
        price = get_live_price(symbol)
    except Exception:
        price = float(df["close"].iloc[-1])

    return {
        "symbol":           symbol,
        "timeframe":        timeframe,
        "htf_timeframe":    htf,
        "live_price":       price,
        "market_state":     market_state,
        "regime":           market_regime,
        "structure":        structure,
        "htf_market_state": htf_market_state,
        "session_context":  session_context,
        "key_levels":       liquidity,
        "setups":           setup_scores,
        "tradeability":     tradeability_verdict(market_state["state_score"]),
    }
