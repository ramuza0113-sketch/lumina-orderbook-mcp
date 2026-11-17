"""
Lumina Live Microstructure, Interactive Candlestick Chart, Order Book & Risk Terminal (v0.3.0).

Runs on Python's built-in `ThreadingHTTPServer` (`127.0.0.1` localhost-only) and renders
a Bloomberg / TradingView-grade 4-module dark terminal in any browser:
  1. Left Panel: Multi-Asset Liquidity & OFI Anomaly Radar (Ranked Watchlist)
  2. Center-Top Panel: Interactive TradingView `lightweight-charts` Candlestick + Volume +
     EMA(20/50/200) + Automatic 1.5R / 3.0R / Stop-Loss & Whale Wall Price Lines!
  3. Center-Bottom Panel: Live 60-Level L2 Order Book DOM Ladder + Cumulative Depth SVG (Crypto)
     OR 24-Bin Volume-at-Price POC/VAH/VAL Histogram (Stocks / Gold / FX)
  4. Right Panel: Closed-Bar Trend Stack, ADR(15) Fuel Tank Gauge & 1.5R / 3.0R Risk Blueprint
"""

from __future__ import annotations

import json
import socket
import threading
import time
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from .core_engine import (
    SPONSOR_URL,
    build_live_quant_candle_packet,
    check_local_institutional_ports,
    fetch_live_orderbook_or_vap,
    scan_multi_asset_anomalies,
)

_SERVER_LOCK = threading.Lock()
_ACTIVE_PORT: int | None = None
_ACTIVE_SERVER: ThreadingHTTPServer | None = None


DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Lumina OrderBook, Chart & Quant Risk Terminal</title>
<script src="https://unpkg.com/lightweight-charts@4.2.0/dist/lightweight-charts.standalone.production.js"></script>
<style>
  :root {
    --bg: #060a12;
    --panel: #0d1422;
    --panel-2: #121c2f;
    --border: #1e2d47;
    --text: #e6eefc;
    --muted: #8ca0c2;
    --cyan: #22d3ee;
    --green: #10b981;
    --green-bg: rgba(16, 185, 129, 0.16);
    --red: #f43f5e;
    --red-bg: rgba(244, 63, 94, 0.16);
    --amber: #f59e0b;
    --violet: #a855f7;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    background: var(--bg);
    color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Hiragino Sans", "Yu Gothic UI", Meiryo, sans-serif;
    font-size: 13px;
  }
  .mono {
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    font-variant-numeric: tabular-nums;
  }
  header {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    padding: 10px 16px;
    background: linear-gradient(90deg, #09101d 0%, #101b30 100%);
    border-bottom: 1px solid var(--border);
    position: sticky;
    top: 0;
    z-index: 30;
  }
  .brand {
    display: flex;
    align-items: center;
    gap: 10px;
    font-weight: 700;
    font-size: 15px;
    letter-spacing: 0.3px;
  }
  .pulse {
    width: 9px; height: 9px; border-radius: 50%;
    background: var(--green);
    box-shadow: 0 0 10px var(--green);
    animation: blink 1.8s infinite;
  }
  @keyframes blink { 0%,100%{opacity:1;} 50%{opacity:0.35;} }
  .controls {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px;
  }
  input, select, button {
    background: var(--panel-2);
    color: var(--text);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 12px;
  }
  button { cursor: pointer; transition: 0.15s; }
  button:hover { border-color: var(--cyan); }
  .tf-btn.active, .line-btn.active {
    background: rgba(34, 211, 238, 0.18);
    border-color: var(--cyan);
    color: var(--cyan);
    font-weight: 700;
  }
  .sponsor-btn {
    background: linear-gradient(135deg, #db2777, #9333ea);
    border: none;
    color: #fff;
    font-weight: 700;
    text-decoration: none;
    padding: 7px 12px;
    border-radius: 6px;
    display: inline-flex;
    align-items: center;
    gap: 6px;
  }
  .sponsor-btn:hover { opacity: 0.92; }
  .grid {
    display: grid;
    grid-template-columns: 300px minmax(460px, 1.45fr) 355px;
    gap: 12px;
    padding: 12px;
    align-items: start;
  }
  .center-stack {
    display: flex;
    flex-direction: column;
    gap: 12px;
    min-width: 0;
  }
  @media (max-width: 1240px) {
    .grid { grid-template-columns: 1fr; }
  }
  .card {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 10px;
    overflow: hidden;
  }
  .card-hd {
    padding: 9px 14px;
    background: rgba(255,255,255,0.02);
    border-bottom: 1px solid var(--border);
    display: flex;
    flex-wrap: wrap;
    justify-content: space-between;
    align-items: center;
    gap: 8px;
    font-weight: 700;
    font-size: 13px;
  }
  .card-bd { padding: 12px 14px; }
  .badge {
    display: inline-block;
    padding: 2px 7px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 700;
  }
  .b-bull { background: var(--green-bg); color: #34d399; border: 1px solid rgba(16,185,129,0.35); }
  .b-bear { background: var(--red-bg); color: #fb7185; border: 1px solid rgba(244,63,94,0.35); }
  .b-neut { background: rgba(140,160,194,0.14); color: var(--muted); border: 1px solid rgba(140,160,194,0.3); }

  /* Chart */
  #tvChartWrap {
    position: relative;
    width: 100%;
    height: 360px;
    background: #070c17;
  }
  .chart-legend {
    position: absolute;
    left: 10px;
    top: 8px;
    z-index: 10;
    pointer-events: none;
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    font-size: 11.5px;
    background: rgba(6, 10, 18, 0.72);
    padding: 4px 8px;
    border-radius: 5px;
    border: 1px solid rgba(30,45,71,0.7);
  }

  /* Watchlist Radar */
  .scan-row {
    padding: 9px 10px;
    border: 1px solid var(--border);
    border-radius: 8px;
    margin-bottom: 8px;
    cursor: pointer;
    background: var(--panel-2);
    transition: 0.15s;
  }
  .scan-row:hover, .scan-row.selected {
    border-color: var(--cyan);
    box-shadow: 0 0 0 1px rgba(34,211,238,0.25);
  }
  .bar-dual {
    position: relative;
    height: 7px;
    background: #09101d;
    border-radius: 4px;
    overflow: hidden;
    margin-top: 6px;
  }
  .bar-dual::after {
    content: "";
    position: absolute;
    left: 50%; top: 0; bottom: 0;
    width: 1px; background: #334155;
  }
  .bar-fill { position: absolute; top: 0; bottom: 0; }

  /* OrderBook Ladder */
  .kpi-strip {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 8px;
    margin-bottom: 10px;
  }
  .kpi {
    background: var(--panel-2);
    border: 1px solid var(--border);
    border-radius: 7px;
    padding: 7px 9px;
  }
  .kpi .lbl { color: var(--muted); font-size: 11px; }
  .kpi .val { font-size: 14px; font-weight: 700; margin-top: 2px; }
  .ladder-row {
    position: relative;
    display: grid;
    grid-template-columns: 1.15fr 0.85fr 1.1fr;
    padding: 3px 8px;
    font-size: 12px;
    border-bottom: 1px solid rgba(255,255,255,0.025);
  }
  .ladder-bg {
    position: absolute;
    top: 1px; bottom: 1px; right: 0;
    pointer-events: none;
  }
  .ladder-row span { position: relative; z-index: 1; }
  .mid-banner {
    padding: 7px 10px;
    margin: 5px 0;
    background: rgba(34, 211, 238, 0.1);
    border: 1px solid rgba(34, 211, 238, 0.35);
    border-radius: 6px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-weight: 700;
  }
  .wall-tag {
    background: rgba(245,158,11,0.22);
    color: #fbbf24;
    padding: 0 5px;
    border-radius: 3px;
    font-size: 10px;
    margin-left: 4px;
  }

  /* VAP Histogram */
  .vap-row {
    position: relative;
    display: flex;
    justify-content: space-between;
    padding: 3px 8px;
    margin-bottom: 2px;
    background: #09101d;
    border-radius: 3px;
    font-size: 11.5px;
  }
  .vap-bar {
    position: absolute;
    left: 0; top: 0; bottom: 0;
    border-radius: 3px;
    pointer-events: none;
  }
  .vap-row span { position: relative; z-index: 1; }

  /* Risk Blueprint */
  .fuel-track {
    height: 12px;
    background: #09101d;
    border: 1px solid var(--border);
    border-radius: 6px;
    overflow: hidden;
    margin-top: 5px;
  }
  .fuel-fill {
    height: 100%;
    background: linear-gradient(90deg, #10b981, #22d3ee);
    transition: width 0.3s;
  }
  .bp-box {
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 10px;
    margin-top: 10px;
    background: var(--panel-2);
  }
  .bp-box.recommended {
    border-color: var(--cyan);
    box-shadow: 0 0 14px rgba(34,211,238,0.12);
  }
  .bp-line {
    display: flex;
    justify-content: space-between;
    padding: 5px 0;
    border-bottom: 1px dashed rgba(255,255,255,0.07);
  }
  .bp-line:last-child { border-bottom: none; }
  .pro-callout {
    margin-top: 12px;
    padding: 10px 12px;
    border-radius: 8px;
    background: linear-gradient(135deg, rgba(219,39,119,0.12), rgba(147,51,234,0.12));
    border: 1px solid rgba(236,72,153,0.35);
    font-size: 12px;
    line-height: 1.5;
  }
</style>
</head>
<body>

<header>
  <div class="brand">
    <div class="pulse"></div>
    <span>🏛️ LUMINA ORDERBOOK, CHART & QUANT RISK TERMINAL</span>
    <span class="badge b-neut mono" id="clockUtc">--:--:--</span>
  </div>
  <div class="controls">
    <input id="symInput" class="mono" value="BTC-USD" style="width:110px;font-weight:700;" placeholder="Symbol..." />
    <button onclick="applySymbolInput()" id="btnLoad">Load</button>
    <div id="tfGroup" style="display:flex;gap:4px;">
      <button class="tf-btn" onclick="setTf('5m')">5m</button>
      <button class="tf-btn" onclick="setTf('15m')">15m</button>
      <button class="tf-btn" onclick="setTf('30m')">30m</button>
      <button class="tf-btn active" onclick="setTf('1h')">1h</button>
      <button class="tf-btn" onclick="setTf('1d')">1d</button>
    </div>
    <select id="refreshSel" onchange="resetTimer()">
      <option value="4000">Auto: 4s</option>
      <option value="12000">Auto: 12s</option>
      <option value="0">Paused</option>
    </select>
    <button onclick="toggleLang()" id="langBtn">🌐 日本語 / EN</button>
    <a class="sponsor-btn" href="https://github.com/sponsors/ramuza0113-sketch" target="_blank" rel="noopener">
      ♡ <span id="sponsorTxt">Sponsor Pro</span>
    </a>
  </div>
</header>

<div class="grid">
  <!-- LEFT: MULTI-ASSET RADAR -->
  <div class="card">
    <div class="card-hd">
      <span id="hdRadar">📡 Multi-Asset OFI & Volume Radar</span>
      <button onclick="loadRadar()" id="btnScan" style="padding:3px 8px;">Scan</button>
    </div>
    <div class="card-bd">
      <div style="display:flex;gap:6px;margin-bottom:10px;">
        <input id="watchInput" class="mono" style="width:100%;" value="BTC-USD,ETH-USD,SOL-USD,NVDA,TSLA,XAUUSD" />
      </div>
      <div id="radarList">Loading radar...</div>
    </div>
  </div>

  <!-- CENTER STACK: TOP = CANDLESTICK CHART, BOTTOM = 60-LEVEL L2 BOOK / VAP -->
  <div class="center-stack">
    <div class="card">
      <div class="card-hd">
        <span id="hdChart">📈 Candlestick Chart + EMA(20/50/200) + Risk Lines</span>
        <div style="display:flex;gap:4px;">
          <button class="line-btn active" id="lineAutoBtn" onclick="setOverlaySide('AUTO')">Auto</button>
          <button class="line-btn" id="lineLongBtn" onclick="setOverlaySide('LONG')">LONG</button>
          <button class="line-btn" id="lineShortBtn" onclick="setOverlaySide('SHORT')">SHORT</button>
          <button class="line-btn" id="lineOffBtn" onclick="setOverlaySide('OFF')">Off</button>
        </div>
      </div>
      <div id="tvChartWrap">
        <div class="chart-legend mono" id="chartLegend">
          <span style="color:#22d3ee;">● EMA20</span>
          <span style="color:#f59e0b;">● EMA50</span>
          <span style="color:#a855f7;">● EMA200</span>
          <span id="ohlcReadout" style="color:var(--text);"></span>
        </div>
      </div>
    </div>

    <div class="card">
      <div class="card-hd">
        <span id="hdBook">📊 Live 60-Level Order Book & Walls</span>
        <span class="badge b-neut mono" id="feedBadge">--</span>
      </div>
      <div class="card-bd" id="bookContainer">Loading microstructure...</div>
    </div>
  </div>

  <!-- RIGHT: CLOSED-BAR QUANT & ATR RISK BLUEPRINT -->
  <div class="card">
    <div class="card-hd">
      <span id="hdRisk">🎯 Closed-Bar Quant & 1.5R/3.0R Risk Map</span>
      <span class="badge b-bull mono" id="antiRepaintBadge">CLOSED-BAR</span>
    </div>
    <div class="card-bd" id="riskContainer">Loading risk blueprint...</div>
  </div>
</div>

<script>
const params = new URLSearchParams(window.location.search);
let currentSym = (params.get("symbol") || "BTC-USD").toUpperCase();
let currentTf = params.get("timeframe") || "1h";
let lang = (navigator.language || "").startsWith("ja") ? "ja" : "en";
let timerId = null;
let overlayMode = "AUTO"; // AUTO | LONG | SHORT | OFF
let lastCandlePacket = null;
let lastOrderBookPacket = null;

// TradingView Lightweight Charts instances
let tvChart = null;
let candleSeries = null;
let volSeries = null;
let ema20Series = null;
let ema50Series = null;
let ema200Series = null;
let activePriceLines = [];

if (params.get("watchlist")) {
  document.getElementById("watchInput").value = params.get("watchlist");
}
document.getElementById("symInput").value = currentSym;

const REGIME_JA = {
  "STRONG_BID_DOMINANCE": "強い買い板優勢",
  "MILD_BID_SUPPORT": "買い板サポート",
  "STRONG_ASK_SUPPLY_WALL": "強い売り壁優勢",
  "MILD_ASK_OVERHANG": "売り板やや優勢",
  "NEUTRAL_EQUILIBRIUM_DEADZONE": "板均衡・中立",
  "INSTITUTIONAL_ACCUMULATION_BIAS": "大口買い集め優位",
  "INSTITUTIONAL_DISTRIBUTION_BIAS": "大口売り捌き優位",
  "TWO_WAY_ROTATION_DEADZONE": "中立様子見（均衡）",
  "BULLISH_TREND_STACK": "上昇トレンド配列 (EMA20>50>200)",
  "BEARISH_TREND_STACK": "下落トレンド配列 (EMA20<50<200)",
  "MIXED_TRANSITION_STACK": "トレンド転換・保ち合い",
  "ABOVE_200D_SMA_STAGE2": "日足200SMA上 (Stage2強気)",
  "BELOW_200D_SMA_DEFENSIVE": "日足200SMA割れ (防御圏)",
  "AGGRESSIVE_TAPE_BUYING": "歩み値：成行買い優勢",
  "AGGRESSIVE_TAPE_SELLING": "歩み値：成行売り優勢",
  "BALANCED_TWO_WAY_TAPE": "歩み値：売買拮抗"
};

function trRegime(code) {
  if (!code) return "--";
  return lang === "ja" && REGIME_JA[code] ? `${REGIME_JA[code]}` : code;
}

function regimeBadgeClass(code) {
  if (!code) return "b-neut";
  if (code.includes("BID") || code.includes("ACCUMULATION") || code.includes("BULLISH") || code.includes("ABOVE") || code.includes("BUYING")) return "b-bull";
  if (code.includes("ASK") || code.includes("DISTRIBUTION") || code.includes("BEARISH") || code.includes("BELOW") || code.includes("SELLING")) return "b-bear";
  return "b-neut";
}

function initTvChart() {
  if (!window.LightweightCharts || tvChart) return;
  const wrap = document.getElementById("tvChartWrap");
  tvChart = LightweightCharts.createChart(wrap, {
    width: wrap.clientWidth,
    height: 360,
    layout: {
      background: { type: "solid", color: "#070c17" },
      textColor: "#8ca0c2",
      fontSize: 11,
    },
    grid: {
      vertLines: { color: "rgba(30, 45, 71, 0.45)" },
      horzLines: { color: "rgba(30, 45, 71, 0.45)" },
    },
    crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
    rightPriceScale: { borderColor: "#1e2d47" },
    timeScale: { borderColor: "#1e2d47", timeVisible: true, secondsVisible: false },
  });

  candleSeries = tvChart.addCandlestickSeries({
    upColor: "#10b981",
    downColor: "#f43f5e",
    borderUpColor: "#10b981",
    borderDownColor: "#f43f5e",
    wickUpColor: "#10b981",
    wickDownColor: "#f43f5e",
  });

  volSeries = tvChart.addHistogramSeries({
    priceFormat: { type: "volume" },
    priceScaleId: "",
  });
  volSeries.priceScale().applyOptions({
    scaleMargins: { top: 0.82, bottom: 0 },
  });

  ema20Series = tvChart.addLineSeries({ color: "#22d3ee", lineWidth: 1, priceLineVisible: false, lastValueVisible: false });
  ema50Series = tvChart.addLineSeries({ color: "#f59e0b", lineWidth: 1, priceLineVisible: false, lastValueVisible: false });
  ema200Series = tvChart.addLineSeries({ color: "#a855f7", lineWidth: 2, priceLineVisible: false, lastValueVisible: false });

  tvChart.subscribeCrosshairMove(param => {
    const el = document.getElementById("ohlcReadout");
    if (!param || !param.time || !param.seriesData) {
      el.textContent = "";
      return;
    }
    const c = param.seriesData.get(candleSeries);
    if (c) {
      el.textContent = `O:${c.open} H:${c.high} L:${c.low} C:${c.close}`;
    }
  });

  window.addEventListener("resize", () => {
    if (tvChart && wrap) {
      tvChart.applyOptions({ width: wrap.clientWidth });
    }
  });
}

function redrawPriceLines() {
  if (!candleSeries || !lastCandlePacket) return;
  activePriceLines.forEach(pl => {
    try { candleSeries.removePriceLine(pl); } catch (e) {}
  });
  activePriceLines = [];

  if (overlayMode === "OFF") return;

  const rm = lastCandlePacket.deterministic_risk_map;
  const align = lastCandlePacket.trend_and_momentum.ema_alignment;
  let side = overlayMode;
  if (side === "AUTO") {
    side = align === "BEARISH_TREND_STACK" ? "SHORT" : "LONG";
  }

  const bp = side === "SHORT" ? rm.short_blueprint : rm.long_blueprint;
  const lines = [
    { price: bp.target_3_0r_runner, color: "#10b981", lineWidth: 2, lineStyle: 2, title: `${side} 3.0R` },
    { price: bp.target_1_5r_partial, color: "#34d399", lineWidth: 1, lineStyle: 2, title: `${side} 1.5R` },
    { price: bp.reference_entry, color: "#22d3ee", lineWidth: 1, lineStyle: 0, title: `Entry` },
    { price: bp.structural_stop_loss, color: "#f43f5e", lineWidth: 2, lineStyle: 2, title: `${side} SL (1.5ATR)` },
  ];

  // Also plot POC or Whale Wall if within chart visual vicinity
  if (lastOrderBookPacket) {
    if (lastOrderBookPacket.asset_class === "EQUITY_ETF_FX" && lastOrderBookPacket.volume_profile_5d) {
      lines.push({
        price: lastOrderBookPacket.volume_profile_5d.point_of_control_poc,
        color: "#f59e0b",
        lineWidth: 1,
        lineStyle: 1,
        title: "POC Wall",
      });
    }
  }

  lines.forEach(cfg => {
    activePriceLines.push(candleSeries.createPriceLine({
      price: cfg.price,
      color: cfg.color,
      lineWidth: cfg.lineWidth,
      lineStyle: cfg.lineStyle,
      axisLabelVisible: true,
      title: cfg.title,
    }));
  });
}

function setOverlaySide(mode) {
  overlayMode = mode;
  document.getElementById("lineAutoBtn").classList.toggle("active", mode === "AUTO");
  document.getElementById("lineLongBtn").classList.toggle("active", mode === "LONG");
  document.getElementById("lineShortBtn").classList.toggle("active", mode === "SHORT");
  document.getElementById("lineOffBtn").classList.toggle("active", mode === "OFF");
  redrawPriceLines();
}

function syncStaticText() {
  document.getElementById("hdRadar").textContent = lang === "ja" ? "📡 一括・板＆出来高インバランス順位" : "📡 Multi-Asset OFI & Volume Radar";
  document.getElementById("hdChart").textContent = lang === "ja" ? `📈 ${currentSym} (${currentTf}) ローソク足チャート ＆ 自動損切り・利確ライン` : `📈 ${currentSym} (${currentTf}) Candlestick Chart + EMA & Risk Lines`;
  document.getElementById("hdBook").textContent = lang === "ja" ? `📊 ${currentSym} リアルタイム60段板 / 価格帯別出来高` : `📊 ${currentSym} Live Order Book & Liquidity Profile`;
  document.getElementById("hdRisk").textContent = lang === "ja" ? `🎯 ${currentSym} (${currentTf}) 確定足リスク設計図` : `🎯 ${currentSym} (${currentTf}) Closed-Bar Risk Map`;
  document.getElementById("btnLoad").textContent = lang === "ja" ? "表示" : "Load";
  document.getElementById("btnScan").textContent = lang === "ja" ? "再スキャン" : "Scan";
  document.getElementById("sponsorTxt").textContent = lang === "ja" ? "米国株60段フル板 Pro版" : "Unlock Pro L2";
  document.querySelectorAll(".tf-btn").forEach(b => {
    b.classList.toggle("active", b.textContent === currentTf);
  });
}

function toggleLang() {
  lang = lang === "ja" ? "en" : "ja";
  syncStaticText();
  refreshMainPanels();
  loadRadar();
}

function applySymbolInput() {
  const v = document.getElementById("symInput").value.trim().toUpperCase();
  if (!v) return;
  currentSym = v;
  syncStaticText();
  refreshMainPanels();
  highlightSelectedRadar();
}

function selectSymbol(sym) {
  currentSym = sym;
  document.getElementById("symInput").value = sym;
  syncStaticText();
  refreshMainPanels();
  highlightSelectedRadar();
}

function setTf(tf) {
  currentTf = tf;
  syncStaticText();
  loadRiskAndChartPacket(true);
}

function highlightSelectedRadar() {
  document.querySelectorAll(".scan-row").forEach(el => {
    el.classList.toggle("selected", el.dataset.sym === currentSym);
  });
}

async function loadRadar() {
  const csv = document.getElementById("watchInput").value.trim();
  const box = document.getElementById("radarList");
  try {
    const r = await fetch(`/api/scan?symbols=${encodeURIComponent(csv)}`);
    const d = await r.json();
    if (!d.ranked_opportunities || !d.ranked_opportunities.length) {
      box.innerHTML = `<div style="color:var(--muted)">No symbols returned.</div>`;
      return;
    }
    box.innerHTML = d.ranked_opportunities.map((item, idx) => {
      const score = Number(item.microstructure_pressure_score || 0);
      const pct = Math.min(50, Math.abs(score) * 50);
      const left = score >= 0 ? 50 : (50 - pct);
      const color = score >= 0 ? "var(--green)" : "var(--red)";
      const sign = score >= 0 ? "+" : "";
      const sel = item.symbol === currentSym ? "selected" : "";
      return `
        <div class="scan-row ${sel}" data-sym="${item.symbol}" onclick="selectSymbol('${item.symbol}')">
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <div>
              <span style="color:var(--muted);font-weight:700;margin-right:5px;">#${idx + 1}</span>
              <strong class="mono" style="font-size:14px;">${item.symbol}</strong>
            </div>
            <span class="mono" style="font-weight:700;">$${Number(item.price).toLocaleString()}</span>
          </div>
          <div style="display:flex;justify-content:space-between;align-items:center;margin-top:5px;">
            <span class="badge ${regimeBadgeClass(item.schmitt_trigger_regime)}">${trRegime(item.schmitt_trigger_regime)}</span>
            <span class="mono" style="color:${color};font-weight:700;">${sign}${score.toFixed(4)}</span>
          </div>
          <div class="bar-dual">
            <div class="bar-fill" style="left:${left}%;width:${pct}%;background:${color};"></div>
          </div>
        </div>
      `;
    }).join("");
  } catch (e) {
    box.innerHTML = `<div style="color:var(--red)">Radar error: ${e}</div>`;
  }
}

function buildDepthSvg(bids, asks) {
  if (!bids.length || !asks.length) return "";
  const W = 460, H = 95;
  const bRev = [...bids].reverse();
  const allPrices = [...bRev.map(x => x.price), ...asks.map(x => x.price)];
  const maxCum = Math.max(bids[bids.length - 1].cum_usd, asks[asks.length - 1].cum_usd, 1);
  const minP = Math.min(...allPrices), maxP = Math.max(...allPrices);
  const spanP = Math.max(maxP - minP, 1e-9);
  const pxX = p => ((p - minP) / spanP) * W;
  const cumY = c => H - (c / maxCum) * (H - 14) - 3;

  const bPts = bRev.map(b => `${pxX(b.price).toFixed(1)},${cumY(b.cum_usd).toFixed(1)}`).join(" ");
  const bArea = `${pxX(bRev[0].price).toFixed(1)},${H} ${bPts} ${pxX(bRev[bRev.length-1].price).toFixed(1)},${H}`;

  const aPts = asks.map(a => `${pxX(a.price).toFixed(1)},${cumY(a.cum_usd).toFixed(1)}`).join(" ");
  const aArea = `${pxX(asks[0].price).toFixed(1)},${H} ${aPts} ${pxX(asks[asks.length-1].price).toFixed(1)},${H}`;

  return `
    <svg viewBox="0 0 ${W} ${H}" style="width:100%;height:95px;background:#080e1a;border:1px solid var(--border);border-radius:7px;margin-bottom:10px;">
      <polygon points="${bArea}" fill="rgba(16,185,129,0.22)" />
      <polyline points="${bPts}" fill="none" stroke="#10b981" stroke-width="2" />
      <polygon points="${aArea}" fill="rgba(244,63,94,0.22)" />
      <polyline points="${aPts}" fill="none" stroke="#f43f5e" stroke-width="2" />
      <text x="8" y="15" fill="#34d399" font-size="10" font-family="monospace">CUM BID DEPTH ($${Math.round(bids[bids.length-1].cum_usd).toLocaleString()})</text>
      <text x="${W - 8}" y="15" text-anchor="end" fill="#fb7185" font-size="10" font-family="monospace">CUM ASK DEPTH ($${Math.round(asks[asks.length-1].cum_usd).toLocaleString()})</text>
    </svg>
  `;
}

async function loadOrderBook() {
  const box = document.getElementById("bookContainer");
  try {
    const r = await fetch(`/api/orderbook?symbol=${encodeURIComponent(currentSym)}`);
    const d = await r.json();
    if (d.error) {
      box.innerHTML = `<div style="color:var(--red)">${d.error}</div>`;
      return;
    }
    lastOrderBookPacket = d;
    document.getElementById("clockUtc").textContent = new Date().toLocaleTimeString();

    if (d.asset_class === "CRYPTO") {
      document.getElementById("feedBadge").textContent = "60-LEVEL L2 LIVE";
      const bids = (d.ladder_levels && d.ladder_levels.bids) || [];
      const asks = (d.ladder_levels && d.ladder_levels.asks) || [];
      const topBidWallPrices = new Set((d.liquidity_walls.largest_bid_support_walls || []).map(w => w.price));
      const topAskWallPrices = new Set((d.liquidity_walls.largest_ask_resistance_walls || []).map(w => w.price));

      const asks12 = asks.slice(0, 12).reverse();
      const bids12 = bids.slice(0, 12);
      const maxNotional = Math.max(
        ...asks12.map(x => x.notional_usd),
        ...bids12.map(x => x.notional_usd),
        1
      );

      const askRows = asks12.map(a => {
        const w = Math.min(100, (a.notional_usd / maxNotional) * 100);
        const wall = topAskWallPrices.has(a.price) ? `<span class="wall-tag">🐋 WALL</span>` : "";
        return `
          <div class="ladder-row mono">
            <div class="ladder-bg" style="width:${w}%;background:rgba(244,63,94,0.16);"></div>
            <span style="color:#fb7185;">${a.price.toLocaleString()}${wall}</span>
            <span style="text-align:right;color:var(--muted);">${a.size}</span>
            <span style="text-align:right;">$${a.notional_usd.toLocaleString()}</span>
          </div>`;
      }).join("");

      const bidRows = bids12.map(b => {
        const w = Math.min(100, (b.notional_usd / maxNotional) * 100);
        const wall = topBidWallPrices.has(b.price) ? `<span class="wall-tag">🐋 WALL</span>` : "";
        return `
          <div class="ladder-row mono">
            <div class="ladder-bg" style="width:${w}%;background:rgba(16,185,129,0.16);"></div>
            <span style="color:#34d399;">${b.price.toLocaleString()}${wall}</span>
            <span style="text-align:right;color:var(--muted);">${b.size}</span>
            <span style="text-align:right;">$${b.notional_usd.toLocaleString()}</span>
          </div>`;
      }).join("");

      const ofi = d.order_flow_imbalance;
      const tape = d.recent_tape_flow || {};
      box.innerHTML = `
        <div class="kpi-strip">
          <div class="kpi">
            <div class="lbl">${lang === "ja" ? "上位10段 買い板比率" : "Top-10 Bid Ratio"}</div>
            <div class="val mono" style="color:${ofi.top10_bid_ratio_pct >= 50 ? 'var(--green)' : 'var(--red)'}">${ofi.top10_bid_ratio_pct}%</div>
          </div>
          <div class="kpi">
            <div class="lbl">${lang === "ja" ? "60段 加重OFI圧力" : "60-Lvl Weighted OFI"}</div>
            <div class="val mono">${ofi.distance_weighted_pressure >= 0 ? '+' : ''}${ofi.distance_weighted_pressure}</div>
          </div>
          <div class="kpi">
            <div class="lbl">${lang === "ja" ? "スプレッド" : "Spread"}</div>
            <div class="val mono">${d.touch.spread_bps} bps</div>
          </div>
        </div>
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;gap:6px;flex-wrap:wrap;">
          <span class="badge ${regimeBadgeClass(ofi.schmitt_trigger_regime)}">${trRegime(ofi.schmitt_trigger_regime)}</span>
          ${tape.available ? `<span class="badge ${regimeBadgeClass(tape.tape_state)}">${trRegime(tape.tape_state)} (${tape.tape_delta_imbalance >= 0 ? '+' : ''}${tape.tape_delta_imbalance})</span>` : ""}
        </div>
        ${buildDepthSvg(bids, asks)}
        <div class="ladder-row" style="color:var(--muted);font-size:11px;border-bottom:1px solid var(--border);">
          <span>${lang === "ja" ? "気配値 (Price)" : "Price (USD)"}</span>
          <span style="text-align:right;">${lang === "ja" ? "数量 (Size)" : "Size"}</span>
          <span style="text-align:right;">${lang === "ja" ? "板金額 (USD)" : "Notional"}</span>
        </div>
        ${askRows}
        <div class="mid-banner mono">
          <span>Mid: $${d.touch.mid_price.toLocaleString()}</span>
          <span style="color:var(--cyan);font-size:12px;">Stoikov Micro: $${d.touch.stoikov_micro_price.toLocaleString()}</span>
        </div>
        ${bidRows}
      `;
    } else {
      document.getElementById("feedBadge").textContent = "5M VAP PROFILE";
      const pv = d.price_and_vwap;
      const vp = d.volume_profile_5d;
      const fl = d.intraday_flow_pressure;
      const hist = d.vap_histogram || [];

      const vapRows = hist.map(row => {
        let color = row.in_value_area ? "rgba(34,211,238,0.22)" : "rgba(140,160,194,0.10)";
        let tag = "";
        if (row.is_poc) {
          color = "rgba(245,158,11,0.38)";
          tag = `<span class="wall-tag">POC (最大出来高壁)</span>`;
        }
        return `
          <div class="vap-row mono">
            <div class="vap-bar" style="width:${row.pct_of_max}%;background:${color};"></div>
            <span>${row.price.toLocaleString()} ${tag}</span>
            <span style="color:var(--muted);">${Number(row.volume).toLocaleString()}</span>
          </div>
        `;
      }).join("");

      box.innerHTML = `
        <div class="kpi-strip">
          <div class="kpi">
            <div class="lbl">${lang === "ja" ? "現在値 / VWAP乖離" : "Price / VWAP Dev"}</div>
            <div class="val mono">${pv.last_price.toLocaleString()} <span style="font-size:11px;color:var(--cyan);">(${pv.vwap_deviation_bps >= 0 ? '+' : ''}${pv.vwap_deviation_bps} bps)</span></div>
          </div>
          <div class="kpi">
            <div class="lbl">POC (${lang === "ja" ? "最頻価格帯" : "Point of Control"})</div>
            <div class="val mono" style="color:var(--amber);">${vp.point_of_control_poc.toLocaleString()}</div>
          </div>
          <div class="kpi">
            <div class="lbl">70% Value Area</div>
            <div class="val mono" style="font-size:12px;">${vp.value_area_low_val_70pct} – ${vp.value_area_high_vah_70pct}</div>
          </div>
        </div>
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
          <span class="badge ${regimeBadgeClass(fl.schmitt_trigger_regime)}">${trRegime(fl.schmitt_trigger_regime)} (${fl.trailing_2h_volume_imbalance >= 0 ? '+' : ''}${fl.trailing_2h_volume_imbalance})</span>
          <span class="mono" style="font-size:11px;color:var(--muted);">Session VWAP: ${pv.session_vwap}</span>
        </div>
        ${vapRows}
        <div class="pro-callout">
          💎 <strong>${lang === "ja" ? "米国株・ETF 60段リアルタイム板 (NASDAQ TotalView)" : "60-Level Live NASDAQ TotalView L2"}</strong>:
          ${lang === "ja"
            ? `ローカル OpenD (:11111) = <code>${d.nasdaq_totalview_60level_l2_bridge.local_moomoo_opend_port_11111}</code>。見せ板（スプーフィング）急キャンセル＆アイスバーグ検知は <a href="https://github.com/sponsors/ramuza0113-sketch" target="_blank" style="color:#f472b6;font-weight:700;">GitHub Sponsors Pro版</a> で解放できます。`
            : `Local OpenD (:11111) = <code>${d.nasdaq_totalview_60level_l2_bridge.local_moomoo_opend_port_11111}</code>. Unlock live 60-depth L2 Spoofing & Iceberg detection via <a href="https://github.com/sponsors/ramuza0113-sketch" target="_blank" style="color:#f472b6;font-weight:700;">GitHub Sponsors Pro</a>.`}
        </div>
      `;
      redrawPriceLines();
    }
  } catch (e) {
    box.innerHTML = `<div style="color:var(--red)">OrderBook error: ${e}</div>`;
  }
}

async function loadRiskAndChartPacket(fitContent = false) {
  const box = document.getElementById("riskContainer");
  try {
    initTvChart();
    const r = await fetch(`/api/candle?symbol=${encodeURIComponent(currentSym)}&timeframe=${encodeURIComponent(currentTf)}&bars=1`);
    const d = await r.json();
    if (d.error) {
      box.innerHTML = `<div style="color:var(--red)">${d.error}</div>`;
      return;
    }
    lastCandlePacket = d;

    // Render Candlestick Chart + Volume + EMA(20/50/200) + Risk Lines
    if (candleSeries && d.chart_bars && d.chart_bars.length) {
      candleSeries.setData(d.chart_bars.map(b => ({
        time: b.time, open: b.open, high: b.high, low: b.low, close: b.close
      })));
      volSeries.setData(d.chart_bars.map(b => ({
        time: b.time,
        value: b.volume,
        color: b.close >= b.open ? "rgba(16,185,129,0.32)" : "rgba(244,63,94,0.32)"
      })));
      ema20Series.setData(d.chart_bars.map(b => ({ time: b.time, value: b.ema20 })));
      ema50Series.setData(d.chart_bars.map(b => ({ time: b.time, value: b.ema50 })));
      ema200Series.setData(d.chart_bars.map(b => ({ time: b.time, value: b.ema200 })));
      redrawPriceLines();
      if (fitContent && tvChart) {
        tvChart.timeScale().fitContent();
      }
    }

    const tm = d.trend_and_momentum;
    const rm = d.deterministic_risk_map;
    const fuel = tm.intraday_adr_fuel_remaining_pct;
    const isBear = tm.ema_alignment === "BEARISH_TREND_STACK";
    const isBull = tm.ema_alignment === "BULLISH_TREND_STACK";

    box.innerHTML = `
      <div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:10px;">
        <span class="badge ${regimeBadgeClass(tm.ema_alignment)}">${trRegime(tm.ema_alignment)}</span>
        <span class="badge ${regimeBadgeClass(tm.weinstein_regime)}">${trRegime(tm.weinstein_regime)}</span>
      </div>

      <div class="kpi-strip">
        <div class="kpi">
          <div class="lbl">${lang === "ja" ? "確定終値" : "Closed Price"}</div>
          <div class="val mono">${d.closed_candle.close.toLocaleString()}</div>
        </div>
        <div class="kpi">
          <div class="lbl">RSI(14) / RVOL</div>
          <div class="val mono">${tm.rsi14} <span style="font-size:11px;color:var(--muted);">/ ${tm.rvol20}x</span></div>
        </div>
        <div class="kpi">
          <div class="lbl">ATR(14)</div>
          <div class="val mono">${tm.atr14} <span style="font-size:11px;color:var(--muted);">(${tm.atr14_pct}%)</span></div>
        </div>
      </div>

      ${fuel !== null && fuel !== undefined ? `
        <div style="margin:10px 0;padding:9px 11px;background:var(--panel-2);border:1px solid var(--border);border-radius:8px;">
          <div style="display:flex;justify-content:space-between;font-size:12px;">
            <span>⛽ ${lang === "ja" ? `本日の残り値幅燃料 (ADR15: ${tm.causal_adr15_pct}%)` : `Intraday ADR15 Fuel Remaining (${tm.causal_adr15_pct}%)`}</span>
            <strong class="mono" style="color:${fuel < 18 ? 'var(--amber)' : 'var(--cyan)'}">${fuel}%</strong>
          </div>
          <div class="fuel-track">
            <div class="fuel-fill" style="width:${Math.min(100, fuel)}%;background:${fuel < 18 ? 'var(--amber)' : 'linear-gradient(90deg,#10b981,#22d3ee)'};"></div>
          </div>
        </div>
      ` : ""}

      <div style="font-size:12px;color:var(--muted);margin-top:6px;">
        📐 ${lang === "ja" ? "$100リスクあたりの適正数量" : "Position Sizing per $100 Risk"}:
        <strong class="mono" style="color:var(--text);">${rm.position_units_per_100usd_risk} units</strong>
        (1.5 ATR = <span class="mono">${rm.stop_distance_1_5_atr}</span>)
      </div>

      <!-- LONG BLUEPRINT -->
      <div class="bp-box ${isBull ? 'recommended' : ''}">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
          <strong style="color:#34d399;">📈 ${lang === "ja" ? "LONG（買い）自動設計図" : "LONG Blueprint"}</strong>
          ${isBull ? `<span class="badge b-bull">${lang === "ja" ? "トレンド合致" : "TREND ALIGNED"}</span>` : ""}
        </div>
        <div class="bp-line mono"><span>🎯 ${lang === "ja" ? "利確② (3.0R ランナー)" : "Target 2 (3.0R)"}</span><strong style="color:#34d399;">${rm.long_blueprint.target_3_0r_runner.toLocaleString()}</strong></div>
        <div class="bp-line mono"><span>💰 ${lang === "ja" ? "利確① (1.5R 分割)" : "Target 1 (1.5R)"}</span><strong style="color:#34d399;">${rm.long_blueprint.target_1_5r_partial.toLocaleString()}</strong></div>
        <div class="bp-line mono"><span>📍 ${lang === "ja" ? "基準価格 (確定足)" : "Reference Entry"}</span><strong>${rm.long_blueprint.reference_entry.toLocaleString()}</strong></div>
        <div class="bp-line mono"><span>🛡️ ${lang === "ja" ? "損切り (1.5 ATR)" : "Stop Loss (1.5 ATR)"}</span><strong style="color:#fb7185;">${rm.long_blueprint.structural_stop_loss.toLocaleString()}</strong></div>
      </div>

      <!-- SHORT BLUEPRINT -->
      <div class="bp-box ${isBear ? 'recommended' : ''}">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
          <strong style="color:#fb7185;">📉 ${lang === "ja" ? "SHORT（売り）自動設計図" : "SHORT Blueprint"}</strong>
          ${isBear ? `<span class="badge b-bear">${lang === "ja" ? "トレンド合致" : "TREND ALIGNED"}</span>` : ""}
        </div>
        <div class="bp-line mono"><span>🛡️ ${lang === "ja" ? "損切り (1.5 ATR)" : "Stop Loss (1.5 ATR)"}</span><strong style="color:#fb7185;">${rm.short_blueprint.structural_stop_loss.toLocaleString()}</strong></div>
        <div class="bp-line mono"><span>📍 ${lang === "ja" ? "基準価格 (確定足)" : "Reference Entry"}</span><strong>${rm.short_blueprint.reference_entry.toLocaleString()}</strong></div>
        <div class="bp-line mono"><span>💰 ${lang === "ja" ? "利確① (1.5R 分割)" : "Target 1 (1.5R)"}</span><strong style="color:#34d399;">${rm.short_blueprint.target_1_5r_partial.toLocaleString()}</strong></div>
        <div class="bp-line mono"><span>🎯 ${lang === "ja" ? "利確② (3.0R ランナー)" : "Target 2 (3.0R)"}</span><strong style="color:#34d399;">${rm.short_blueprint.target_3_0r_runner.toLocaleString()}</strong></div>
      </div>

      <div style="margin-top:8px;font-size:11px;color:var(--muted);" class="mono">
        Confirmed Bar: ${d.anti_repaint_guard.confirmed_bar_timestamp}
      </div>
    `;
  } catch (e) {
    box.innerHTML = `<div style="color:var(--red)">Risk packet error: ${e}</div>`;
  }
}

function refreshMainPanels() {
  loadOrderBook();
  loadRiskAndChartPacket(true);
}

function resetTimer() {
  if (timerId) clearInterval(timerId);
  const ms = Number(document.getElementById("refreshSel").value || 0);
  if (ms > 0) {
    timerId = setInterval(() => {
      loadOrderBook();
    }, ms);
  }
}

document.getElementById("symInput").addEventListener("keydown", e => {
  if (e.key === "Enter") applySymbolInput();
});

syncStaticText();
loadRadar();
refreshMainPanels();
resetTimer();
</script>
</body>
</html>
"""


class _TerminalRequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:
        return

    def _send_json(self, payload: dict[str, Any], status: int = 200) -> None:
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed.query)

        if parsed.path in ("/", "/index.html"):
            body = DASHBOARD_HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if parsed.path == "/api/orderbook":
            sym = qs.get("symbol", ["BTC-USD"])[0]
            try:
                self._send_json(fetch_live_orderbook_or_vap(symbol=sym, depth=60))
            except Exception as exc:
                self._send_json({"error": str(exc), "symbol": sym}, status=200)
            return

        if parsed.path == "/api/candle":
            sym = qs.get("symbol", ["BTC-USD"])[0]
            tf = qs.get("timeframe", ["1h"])[0]
            want_bars = qs.get("bars", ["0"])[0] == "1"
            try:
                self._send_json(
                    build_live_quant_candle_packet(
                        symbol=sym,
                        timeframe=tf,
                        include_chart_bars=want_bars,
                    )
                )
            except Exception as exc:
                self._send_json({"error": str(exc), "symbol": sym}, status=200)
            return

        if parsed.path == "/api/scan":
            syms = qs.get("symbols", ["BTC-USD,ETH-USD,SOL-USD,NVDA,TSLA,XAUUSD"])[0]
            try:
                self._send_json(scan_multi_asset_anomalies(symbols_csv=syms))
            except Exception as exc:
                self._send_json({"error": str(exc)}, status=200)
            return

        if parsed.path == "/api/bridge":
            self._send_json(check_local_institutional_ports())
            return

        self._send_json({"error": "Not found"}, status=404)


def _find_free_port(preferred: int = 8765) -> int:
    for p in (preferred, 8766, 8767, 8768, 0):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("127.0.0.1", p))
                return int(s.getsockname()[1])
        except OSError:
            continue
    return preferred


def ensure_dashboard_server(preferred_port: int = 8765) -> int:
    """Start the background localhost HTTP dashboard server if not already running."""
    global _ACTIVE_PORT, _ACTIVE_SERVER
    with _SERVER_LOCK:
        if _ACTIVE_SERVER is not None and _ACTIVE_PORT is not None:
            return _ACTIVE_PORT
        port = _find_free_port(preferred_port)
        srv = ThreadingHTTPServer(("127.0.0.1", port), _TerminalRequestHandler)
        t = threading.Thread(target=srv.serve_forever, name="lumina-dashboard-http", daemon=True)
        t.start()
        _ACTIVE_SERVER = srv
        _ACTIVE_PORT = port
        return port


def launch_live_terminal(
    symbol: str = "BTC-USD",
    watchlist: str = "BTC-USD,ETH-USD,SOL-USD,NVDA,TSLA,XAUUSD",
    timeframe: str = "1h",
    open_browser: bool = True,
) -> dict[str, Any]:
    """Launch the localhost live web terminal and optionally open the user's browser."""
    port = ensure_dashboard_server()
    query = urllib.parse.urlencode(
        {
            "symbol": symbol.strip().upper(),
            "timeframe": timeframe.strip().lower(),
            "watchlist": watchlist,
        }
    )
    url = f"http://127.0.0.1:{port}/?{query}"
    if open_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass
    return {
        "status": "LIVE_TERMINAL_RUNNING",
        "terminal_url": url,
        "focused_symbol": symbol.strip().upper(),
        "timeframe": timeframe,
        "watchlist": watchlist,
        "features": [
            "Interactive TradingView Candlestick Chart + Volume + EMA(20/50/200) + Automatic 1.5R/3.0R/Stop-Loss Lines",
            "Real-time auto-refreshing 60-Level L2 Order Book DOM Ladder + Cumulative Depth Chart",
            "Multi-Asset Liquidity & OFI Anomaly Ranking (click any symbol to inspect)",
            "Closed-Bar Trend Stack, Intraday ADR15 Fuel Tank Gauge & 1.5R / 3.0R Risk Blueprints",
        ],
        "pro_sponsor_url": SPONSOR_URL,
    }


def run_standalone_dashboard_blocking(symbol: str = "BTC-USD") -> None:
    """Run dashboard in foreground when invoked via `lumina-orderbook-mcp --dashboard`."""
    info = launch_live_terminal(symbol=symbol, open_browser=True)
    print(f"Lumina Live Quant Terminal running at: {info['terminal_url']}", flush=True)
    print("Press Ctrl+C to stop.", flush=True)
    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        pass
