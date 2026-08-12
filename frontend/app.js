const DEFAULT_SETUPS = [
  "Trend Following", "Trend Pullback", "Breakout", "Breakout Retest",
  "Mean Reversion", "Liquidity Sweep", "Compression Expansion", "Opening Range Breakout",
];

const VERDICT_ICON = { Favorable: "🟢", Selective: "🟡", "Low Edge": "🟠", Avoid: "🔴" };

const apiBaseInput = document.getElementById("api-base");
const apiStatus = document.getElementById("api-status");
const setupsContainer = document.getElementById("setups-checkboxes");
const resultsEl = document.getElementById("results");

function getApiBase() {
  return (localStorage.getItem("apiBase") || "").replace(/\/$/, "");
}

function renderSetupCheckboxes(names) {
  setupsContainer.innerHTML = "";
  names.forEach((name) => {
    const label = document.createElement("label");
    const box = document.createElement("input");
    box.type = "checkbox";
    box.value = name;
    box.checked = true;
    label.appendChild(box);
    label.append(name);
    setupsContainer.appendChild(label);
  });
}

function selectedSetups() {
  return Array.from(setupsContainer.querySelectorAll("input:checked")).map((el) => el.value);
}

async function checkApiHealth() {
  const base = getApiBase();
  if (!base) {
    apiStatus.textContent = "Enter your Railway backend URL above and click Save.";
    apiStatus.className = "hint";
    return;
  }
  try {
    const r = await fetch(`${base}/health`, { signal: AbortSignal.timeout(5000) });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    apiStatus.textContent = `Connected: ${base}`;
    apiStatus.className = "hint ok";
    try {
      const s = await (await fetch(`${base}/setups`)).json();
      renderSetupCheckboxes(s.setups || DEFAULT_SETUPS);
    } catch {
      renderSetupCheckboxes(DEFAULT_SETUPS);
    }
  } catch (e) {
    apiStatus.textContent = `Could not reach backend: ${e.message}`;
    apiStatus.className = "hint err";
    renderSetupCheckboxes(DEFAULT_SETUPS);
  }
}

document.getElementById("save-api-base").addEventListener("click", () => {
  localStorage.setItem("apiBase", apiBaseInput.value.trim());
  checkApiHealth();
});

function fmtPrice(v) {
  if (v === null || v === undefined) return "-";
  return v >= 20 ? `$${v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
                 : `$${v}`;
}

function kvRows(pairs) {
  return pairs.map(([k, v]) => `<div><span>${k}</span><span>${v}</span></div>`).join("");
}

function render(env) {
  const est = env.market_state, regime = env.regime, structure = env.structure;
  const sess = env.session_context, levels = env.key_levels, setups = env.setups, verdict = env.tradeability;
  const icon = VERDICT_ICON[verdict] || "⚪";

  const condRows = [
    ["Trend Quality", est.state_trend_quality],
    ["Velocity", est.state_velocity],
    ["Volatility Expansion", est.state_expansion],
    ["Choppiness (inv, high=good)", est.state_anti_chop],
    ["Structure", structure.structure_label],
    ["Directional Regime", regime.regime],
  ];

  const setupRows = setups.ranked.map(
    (s) => `<tr><td>${s.setup}</td><td class="stars">${s.stars}</td><td>${s.score}</td></tr>`
  ).join("");

  let closing = "";
  if (setups.preferred.length) {
    closing += `<div class="banner preferred"><strong>Preferred approaches:</strong> ${setups.preferred.join(", ")}</div>`;
  }
  if (setups.avoid.length) {
    closing += `<div class="banner avoid"><strong>Avoid:</strong> ${setups.avoid.join(", ")}</div>`;
  }
  if (verdict === "Low Edge" || verdict === "Avoid" || !setups.preferred.length) {
    closing += `<div class="banner notrade">No trade signal. Wait for one of your preferred setups to develop.</div>`;
  }

  resultsEl.innerHTML = `
    <section class="panel">
      <div class="headline">
        <span class="dot">${icon}</span>
        <h2>${env.symbol} · "${est.state_label}" · ${est.state_score}/100 · ${verdict}</h2>
      </div>
      <p class="sub-caption">Live: ${fmtPrice(env.live_price)} · HTF (${env.htf_timeframe}) state: "${env.htf_market_state.state_label}" (${env.htf_market_state.state_score}/100)</p>
      <h3>Market Condition</h3>
      <table><tbody>${condRows.map(([k, v]) => `<tr><th>${k}</th><td>${v}</td></tr>`).join("")}</tbody></table>
    </section>

    <section class="panel">
      <h2>Session · Current: ${sess.current_session} · Previous: ${sess.previous_session}</h2>
      <div class="two-col">
        <div>
          <p class="sub-caption">${sess.previous_session} (completed)</p>
          <div class="kv">${kvRows([
            ["Open", fmtPrice(sess.previous_session_open)],
            ["High", fmtPrice(sess.previous_session_high)],
            ["Low", fmtPrice(sess.previous_session_low)],
            ["Close", fmtPrice(sess.previous_session_close)],
            ["Range", sess.previous_session_stats.range],
            ["Direction", sess.previous_session_stats.direction],
            ["Efficiency", sess.previous_session_stats.efficiency],
          ])}</div>
        </div>
        <div>
          <p class="sub-caption">${sess.current_session} (running)</p>
          <div class="kv">${kvRows([
            ["Open", fmtPrice(sess.current_session_open)],
            ["High", fmtPrice(sess.current_session_high)],
            ["Low", fmtPrice(sess.current_session_low)],
            ["Range so far", sess.current_session_range],
            ["Return so far", `${sess.current_session_return_pct}%`],
            ["vs prev close", `${sess.price_vs_prev_close_pct}%`],
          ])}</div>
        </div>
      </div>
    </section>

    <section class="panel">
      <h2>Key Levels</h2>
      <div class="two-col">
        <div class="kv">${kvRows([
          ["Resistance (PDH)", fmtPrice(levels.pdh)],
          ["Equal Highs", fmtPrice(levels.equal_highs_level)],
        ])}</div>
        <div class="kv">${kvRows([
          ["Support (PDL)", fmtPrice(levels.pdl)],
          ["Equal Lows", fmtPrice(levels.equal_lows_level)],
        ])}</div>
      </div>
    </section>

    <section class="panel">
      <h2>Setup Compatibility</h2>
      <table>
        <thead><tr><th>Setup</th><th>Stars</th><th>Score</th></tr></thead>
        <tbody>${setupRows}</tbody>
      </table>
    </section>

    ${closing}
  `;
}

async function analyze() {
  const base = getApiBase();
  if (!base) {
    resultsEl.innerHTML = `<div class="banner error">Set your backend URL above first.</div>`;
    return;
  }
  const symbol = document.getElementById("symbol").value.trim() || "XAUUSD";
  const timeframe = document.getElementById("timeframe").value;
  const setups = selectedSetups();

  resultsEl.innerHTML = `<p class="sub-caption">Loading...</p>`;
  try {
    const params = new URLSearchParams({ timeframe, setups: setups.join(",") });
    const r = await fetch(`${base}/regime/${symbol}?${params}`, { signal: AbortSignal.timeout(30000) });
    if (!r.ok) {
      const body = await r.json().catch(() => ({}));
      throw new Error(body.detail || `HTTP ${r.status}`);
    }
    render(await r.json());
  } catch (e) {
    resultsEl.innerHTML = `<div class="banner error">Request failed: ${e.message}</div>`;
  }
}

document.getElementById("analyze").addEventListener("click", analyze);

// Init
apiBaseInput.value = getApiBase();
renderSetupCheckboxes(DEFAULT_SETUPS);
checkApiHealth().then(() => {
  if (getApiBase()) analyze();
});
