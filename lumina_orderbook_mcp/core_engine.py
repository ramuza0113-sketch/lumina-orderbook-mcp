"""
Deterministic Market Microstructure, L2 Order Book Imbalance (OFI),
Schmitt-Trigger Factor Ontology, and Closed-Bar Risk Engine.

Design Principle ("LLM nodes should argue about meaning, code should own numbers"):
  - Zero LLM arithmetic: all spreads, OFI weights, liquidity walls, ATR stops,
    and R-multiple targets are computed deterministically in IEEE-754 float64.
  - Strictly Stdio-Safe: third-party stdout noise is redirected to stderr so
    Model Context Protocol (MCP) JSON-RPC frames are never corrupted.
  - Zero API Keys Required (BYOD): queries public zero-auth L2 exchange feeds
    (Coinbase Exchange -> Kraken -> Hyperliquid) for 24/7 crypto L2 books and
    intraday Volume-at-Price (VAP) microstructure for global equities/ETFs/FX.

References:
  - Cont, R., Kukanov, A., & Stoikov, S. (2014). The Price Impact of Order Book Events.
  - Hashimoto, K. (2026a). Zenodo DOI: 10.5281/zenodo.23935930 (Deep OFI & Schmitt-Trigger Ontology).
  - Hashimoto, K. (2026d). Zenodo DOI: 10.5281/zenodo.24050440 (Deterministic Guardrails).
"""

from __future__ import annotations

import contextlib
import datetime as dt
import json
import math
import socket
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import pandas as pd

SPONSOR_URL = "https://github.com/sponsors/ramuza0113-sketch"
MAIN_FRAMEWORK_URL = "https://github.com/ramuza0113-sketch/lumina-ai-hedge-fund"

KNOWN_CRYPTO_BASES = {
    "BTC", "ETH", "SOL", "XRP", "DOGE", "ADA", "AVAX", "LINK",
    "DOT", "NEAR", "SUI", "APT", "ARB", "OP", "LTC", "BCH",
    "UNI", "AAVE", "PEPE", "SHIB", "HYPE", "RENDER", "INJ", "TIA",
}

KRAKEN_PAIR_MAP = {
    "BTC": "XXBTZUSD",
    "ETH": "XETHZUSD",
    "SOL": "SOLUSD",
    "XRP": "XXRPZUSD",
    "DOGE": "XDGUSD",
    "ADA": "ADAUSD",
    "AVAX": "AVAXUSD",
    "LINK": "LINKUSD",
    "DOT": "DOTUSD",
    "LTC": "XLTCZUSD",
}


def _clean_float(val: Any, digits: int = 6, default: float = 0.0) -> float:
    """Convert any numeric value to finite Python float without NaN/Inf."""
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return default
        return round(f, digits)
    except (TypeError, ValueError):
        return default


def _price_digits(price: float) -> int:
    """Adaptive decimal precision based on asset price magnitude."""
    p = abs(price)
    if p >= 1000.0:
        return 2
    if p >= 10.0:
        return 3
    if p >= 1.0:
        return 4
    if p >= 0.01:
        return 6
    return 8


def _http_get_json(url: str, timeout: float = 6.0) -> Any:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "lumina-orderbook-mcp/0.1 (+https://github.com/ramuza0113-sketch/lumina-orderbook-mcp)",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _http_post_json(url: str, payload: dict[str, Any], timeout: float = 6.0) -> Any:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "User-Agent": "lumina-orderbook-mcp/0.1",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def normalize_symbol_info(raw_symbol: str) -> dict[str, Any]:
    """Classify user symbol into crypto pair vs Yahoo Finance equity/FX/commodity ticker."""
    s = (raw_symbol or "BTC-USD").strip().upper()
    s_clean = s.replace("/", "-")

    # Explicit crypto formats: BTC, BTC-USD, BTCUSDT, ETH/USD
    if s_clean.endswith("-USD") or s_clean.endswith("-USDT"):
        base = s_clean.split("-")[0]
        if base in KNOWN_CRYPTO_BASES:
            return {"asset_class": "CRYPTO", "base": base, "yf_symbol": f"{base}-USD"}

    if s_clean.endswith("USDT") and len(s_clean) > 4:
        base = s_clean[:-4]
        if base in KNOWN_CRYPTO_BASES:
            return {"asset_class": "CRYPTO", "base": base, "yf_symbol": f"{base}-USD"}

    if s_clean in KNOWN_CRYPTO_BASES:
        return {"asset_class": "CRYPTO", "base": s_clean, "yf_symbol": f"{s_clean}-USD"}

    # Common convenience aliases for gold / silver / FX
    aliases = {
        "XAUUSD": "GC=F",
        "GOLD": "GC=F",
        "XAGUSD": "SI=F",
        "USDJPY": "USDJPY=X",
        "EURUSD": "EURUSD=X",
        "GBPUSD": "GBPUSD=X",
    }
    yf_sym = aliases.get(s_clean, s_clean)
    return {"asset_class": "EQUITY_ETF_FX", "base": s_clean, "yf_symbol": yf_sym}


def check_tcp_port(host: str, port: int, timeout: float = 0.25) -> bool:
    """Local read-only TCP socket check on 127.0.0.1 to detect running institutional gateways."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def check_local_institutional_ports() -> dict[str, Any]:
    """Inspect localhost institutional L2 / execution gateways (zero external network traffic)."""
    moomoo_open = check_tcp_port("127.0.0.1", 11111)
    ibkr_gateway_paper = check_tcp_port("127.0.0.1", 4002)
    ibkr_gateway_live = check_tcp_port("127.0.0.1", 4001)
    ibkr_tws_paper = check_tcp_port("127.0.0.1", 7497)
    ibkr_tws_live = check_tcp_port("127.0.0.1", 7496)
    mt5_bridge = check_tcp_port("127.0.0.1", 8001)

    ibkr_any = any([ibkr_gateway_paper, ibkr_gateway_live, ibkr_tws_paper, ibkr_tws_live])
    return {
        "timestamp_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "edition": "Open-Source Community Edition (MIT)",
        "localhost_gateways": {
            "moomoo_opend_nasdaq_totalview_11111": "DETECTED_ONLINE" if moomoo_open else "NOT_RUNNING",
            "ibkr_gateway_or_tws": "DETECTED_ONLINE" if ibkr_any else "NOT_RUNNING",
            "ibkr_ports_detail": {
                "4002_gateway_paper": ibkr_gateway_paper,
                "4001_gateway_live": ibkr_gateway_live,
                "7497_tws_paper": ibkr_tws_paper,
                "7496_tws_live": ibkr_tws_live,
            },
            "mt5_rpyc_bridge_8001": "DETECTED_ONLINE" if mt5_bridge else "NOT_RUNNING",
        },
        "pro_tier_capabilities": {
            "sponsor_url": SPONSOR_URL,
            "monthly_pro_tier": "$25/month via GitHub Sponsors (0% platform markup)",
            "unlocks": [
                "Live 60-level NASDAQ TotalView & NYSE Arca L2 Order Book via local Moomoo OpenD (:11111)",
                "Millisecond Spoofing Wall-Collapse & Iceberg Absorption Sentinel",
                "Scroll-Out Resistant Deep OFI (Hashimoto 2026a, Zenodo DOI: 10.5281/zenodo.23935930)",
                "Z3 Theorem-Proved Risk & Slippage-Proof Pyramiding Guardrails",
            ],
        },
    }


def analyze_l2_book_arrays(
    bids: list[tuple[float, float]],
    asks: list[tuple[float, float]],
    depth: int = 60,
    recent_trades: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Pure deterministic L2 order book analyzer.
    Inputs:
      bids: list of (price, size) sorted descending by price
      asks: list of (price, size) sorted ascending by price
    """
    depth = max(5, min(int(depth), 100))
    clean_bids = sorted(
        [(float(p), float(q)) for p, q in bids if float(p) > 0 and float(q) > 0],
        key=lambda x: x[0],
        reverse=True,
    )[:depth]
    clean_asks = sorted(
        [(float(p), float(q)) for p, q in asks if float(p) > 0 and float(q) > 0],
        key=lambda x: x[0],
    )[:depth]

    if not clean_bids or not clean_asks:
        raise ValueError("Order book levels are empty or invalid.")

    best_bid, best_bid_sz = clean_bids[0]
    best_ask, best_ask_sz = clean_asks[0]
    mid_price = 0.5 * (best_bid + best_ask)
    digits = _price_digits(mid_price)

    spread_abs = max(0.0, best_ask - best_bid)
    spread_bps = (spread_abs / mid_price) * 10000.0 if mid_price > 0 else 0.0

    # Top-10 & Full-Depth Imbalance: (BidVol - AskVol) / (BidVol + AskVol) in [-1, +1]
    top10_bid_vol = sum(q for _, q in clean_bids[:10])
    top10_ask_vol = sum(q for _, q in clean_asks[:10])
    top10_tot = top10_bid_vol + top10_ask_vol
    top10_imbalance = (top10_bid_vol - top10_ask_vol) / top10_tot if top10_tot > 0 else 0.0
    top10_bid_ratio_pct = (top10_bid_vol / top10_tot * 100.0) if top10_tot > 0 else 50.0

    deep_bid_vol = sum(q for _, q in clean_bids)
    deep_ask_vol = sum(q for _, q in clean_asks)
    deep_tot = deep_bid_vol + deep_ask_vol
    deep_imbalance = (deep_bid_vol - deep_ask_vol) / deep_tot if deep_tot > 0 else 0.0
    deep_bid_ratio_pct = (deep_bid_vol / deep_tot * 100.0) if deep_tot > 0 else 50.0

    # Exponentially Distance-Weighted Order Book Pressure (decay lambda = 0.12 per level)
    # Gives higher micro-price weight to near-touch liquidity while retaining deep walls.
    w_bid = sum(q * math.exp(-0.12 * idx) for idx, (_, q) in enumerate(clean_bids))
    w_ask = sum(q * math.exp(-0.12 * idx) for idx, (_, q) in enumerate(clean_asks))
    w_tot = w_bid + w_ask
    weighted_pressure = (w_bid - w_ask) / w_tot if w_tot > 0 else 0.0

    # Micro-price (Stoikov volume-weighted touch fair value)
    touch_tot = best_bid_sz + best_ask_sz
    micro_price = (
        (best_bid * best_ask_sz + best_ask * best_bid_sz) / touch_tot
        if touch_tot > 0
        else mid_price
    )

    # Identify Top-3 Bid Support Walls & Top-3 Ask Resistance Walls by notional value
    bid_walls_sorted = sorted(clean_bids, key=lambda x: x[0] * x[1], reverse=True)[:3]
    ask_walls_sorted = sorted(clean_asks, key=lambda x: x[0] * x[1], reverse=True)[:3]

    bid_walls = [
        {
            "price": _clean_float(p, digits),
            "size": _clean_float(q, 6),
            "notional_usd": _clean_float(p * q, 2),
            "distance_bps": _clean_float(((mid_price - p) / mid_price) * 10000.0, 2),
        }
        for p, q in bid_walls_sorted
    ]
    ask_walls = [
        {
            "price": _clean_float(p, digits),
            "size": _clean_float(q, 6),
            "notional_usd": _clean_float(p * q, 2),
            "distance_bps": _clean_float(((p - mid_price) / mid_price) * 10000.0, 2),
        }
        for p, q in ask_walls_sorted
    ]

    # Schmitt-Trigger Microstructure Regime Label (dead-zone [-0.12, +0.12] prevents noise flipping)
    if weighted_pressure >= 0.28:
        book_regime = "STRONG_BID_DOMINANCE"
    elif weighted_pressure >= 0.12:
        book_regime = "MILD_BID_SUPPORT"
    elif weighted_pressure <= -0.28:
        book_regime = "STRONG_ASK_SUPPLY_WALL"
    elif weighted_pressure <= -0.12:
        book_regime = "MILD_ASK_OVERHANG"
    else:
        book_regime = "NEUTRAL_EQUILIBRIUM_DEADZONE"

    tape_summary: dict[str, Any] = {"available": False}
    if recent_trades:
        buy_vol = sum(float(t["size"]) for t in recent_trades if t.get("aggressor") == "BUY")
        sell_vol = sum(float(t["size"]) for t in recent_trades if t.get("aggressor") == "SELL")
        tot_t = buy_vol + sell_vol
        net_delta = (buy_vol - sell_vol) / tot_t if tot_t > 0 else 0.0
        tape_summary = {
            "available": True,
            "sample_trades": len(recent_trades),
            "aggressive_buy_volume": _clean_float(buy_vol, 6),
            "aggressive_sell_volume": _clean_float(sell_vol, 6),
            "tape_delta_imbalance": _clean_float(net_delta, 4),
            "tape_state": (
                "AGGRESSIVE_TAPE_BUYING"
                if net_delta >= 0.18
                else ("AGGRESSIVE_TAPE_SELLING" if net_delta <= -0.18 else "BALANCED_TWO_WAY_TAPE")
            ),
        }

    # Build Top-25 Price Ladder + Cumulative Notional Depth for DOM & Depth Chart rendering
    ladder_depth = min(25, len(clean_bids), len(clean_asks))
    bid_ladder: list[dict[str, float]] = []
    cum_bid_usd = 0.0
    for p, q in clean_bids[:ladder_depth]:
        usd = p * q
        cum_bid_usd += usd
        bid_ladder.append(
            {
                "price": _clean_float(p, digits),
                "size": _clean_float(q, 6),
                "notional_usd": _clean_float(usd, 2),
                "cum_usd": _clean_float(cum_bid_usd, 2),
            }
        )

    ask_ladder: list[dict[str, float]] = []
    cum_ask_usd = 0.0
    for p, q in clean_asks[:ladder_depth]:
        usd = p * q
        cum_ask_usd += usd
        ask_ladder.append(
            {
                "price": _clean_float(p, digits),
                "size": _clean_float(q, 6),
                "notional_usd": _clean_float(usd, 2),
                "cum_usd": _clean_float(cum_ask_usd, 2),
            }
        )

    return {
        "levels_analyzed": {"bids": len(clean_bids), "asks": len(clean_asks)},
        "touch": {
            "best_bid": _clean_float(best_bid, digits),
            "best_bid_size": _clean_float(best_bid_sz, 6),
            "best_ask": _clean_float(best_ask, digits),
            "best_ask_size": _clean_float(best_ask_sz, 6),
            "mid_price": _clean_float(mid_price, digits),
            "stoikov_micro_price": _clean_float(micro_price, digits),
            "spread_abs": _clean_float(spread_abs, digits),
            "spread_bps": _clean_float(spread_bps, 2),
        },
        "order_flow_imbalance": {
            "top10_bid_ratio_pct": _clean_float(top10_bid_ratio_pct, 2),
            "top10_imbalance": _clean_float(top10_imbalance, 4),
            "deep_bid_ratio_pct": _clean_float(deep_bid_ratio_pct, 2),
            "deep_imbalance": _clean_float(deep_imbalance, 4),
            "distance_weighted_pressure": _clean_float(weighted_pressure, 4),
            "schmitt_trigger_regime": book_regime,
        },
        "liquidity_walls": {
            "largest_bid_support_walls": bid_walls,
            "largest_ask_resistance_walls": ask_walls,
        },
        "ladder_levels": {
            "bids": bid_ladder,
            "asks": ask_ladder,
        },
        "recent_tape_flow": tape_summary,
    }


def _fetch_crypto_l2_multi_exchange(base: str, depth: int = 60) -> dict[str, Any]:
    """
    Multi-exchange zero-auth L2 book fetcher with automatic geographic/rate-limit fallback:
      1. Coinbase Exchange (US/EU/JP friendly, regulated L2 book + tape)
      2. Kraken Public Depth API
      3. Hyperliquid L2 Book API
    """
    errors: list[str] = []

    # 1. Coinbase Exchange
    try:
        pair = f"{base}-USD"
        book = _http_get_json(f"https://api.exchange.coinbase.com/products/{pair}/book?level=2")
        raw_bids = [(float(row[0]), float(row[1])) for row in book.get("bids", [])[:depth]]
        raw_asks = [(float(row[0]), float(row[1])) for row in book.get("asks", [])[:depth]]
        trades_raw: list[dict[str, Any]] = []
        try:
            t_resp = _http_get_json(f"https://api.exchange.coinbase.com/products/{pair}/trades?limit=60")
            if isinstance(t_resp, list):
                # Note: on Coinbase `/trades`, `side` is the MAKER side ("buy" maker = SELL aggressor)
                for t in t_resp[:60]:
                    maker_side = str(t.get("side", "")).lower()
                    aggressor = "SELL" if maker_side == "buy" else "BUY"
                    trades_raw.append({"price": float(t["price"]), "size": float(t["size"]), "aggressor": aggressor})
        except Exception:
            trades_raw = []

        if raw_bids and raw_asks:
            metrics = analyze_l2_book_arrays(raw_bids, raw_asks, depth=depth, recent_trades=trades_raw)
            return {
                "symbol": f"{base}-USD",
                "asset_class": "CRYPTO",
                "feed_type": "LIVE_L2_LIMIT_ORDER_BOOK",
                "exchange_source": "Coinbase Exchange (Zero-Auth L2)",
                "timestamp_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                **metrics,
            }
    except Exception as exc:
        errors.append(f"Coinbase: {type(exc).__name__}")

    # 2. Kraken Public API
    try:
        k_pair = KRAKEN_PAIR_MAP.get(base, f"{base}USD")
        resp = _http_get_json(f"https://api.kraken.com/0/public/Depth?pair={k_pair}&count={min(depth, 100)}")
        if not resp.get("error") and resp.get("result"):
            first_key = next(iter(resp["result"]))
            book = resp["result"][first_key]
            raw_bids = [(float(r[0]), float(r[1])) for r in book.get("bids", [])[:depth]]
            raw_asks = [(float(r[0]), float(r[1])) for r in book.get("asks", [])[:depth]]
            if raw_bids and raw_asks:
                metrics = analyze_l2_book_arrays(raw_bids, raw_asks, depth=depth)
                return {
                    "symbol": f"{base}-USD",
                    "asset_class": "CRYPTO",
                    "feed_type": "LIVE_L2_LIMIT_ORDER_BOOK",
                    "exchange_source": "Kraken Spot Public L2",
                    "timestamp_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                    **metrics,
                }
    except Exception as exc:
        errors.append(f"Kraken: {type(exc).__name__}")

    # 3. Hyperliquid L2 Snapshot
    try:
        hl_book = _http_post_json("https://api.hyperliquid.xyz/info", {"type": "l2Book", "coin": base})
        levels = hl_book.get("levels", [])
        if isinstance(levels, list) and len(levels) >= 2:
            raw_bids = [(float(x["px"]), float(x["sz"])) for x in levels[0][:depth]]
            raw_asks = [(float(x["px"]), float(x["sz"])) for x in levels[1][:depth]]
            if raw_bids and raw_asks:
                metrics = analyze_l2_book_arrays(raw_bids, raw_asks, depth=depth)
                return {
                    "symbol": f"{base}-USD",
                    "asset_class": "CRYPTO",
                    "feed_type": "LIVE_L2_LIMIT_ORDER_BOOK",
                    "exchange_source": "Hyperliquid L1 Perp L2",
                    "timestamp_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                    **metrics,
                }
    except Exception as exc:
        errors.append(f"Hyperliquid: {type(exc).__name__}")

    raise RuntimeError(f"Could not fetch live L2 order book for {base} ({'; '.join(errors)})")


def _download_yf_safe(symbol: str, period: str, interval: str) -> pd.DataFrame:
    """Download OHLCV via yfinance while strictly routing any third-party stdout noise to stderr."""
    import pandas as pd
    import yfinance as yf

    with contextlib.redirect_stdout(sys.stderr):
        df = yf.Ticker(symbol).history(period=period, interval=interval, auto_adjust=False)
    if df is None or df.empty:
        raise ValueError(f"No market data returned for '{symbol}' (period={period}, interval={interval}).")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]
    return df.dropna(subset=["Open", "High", "Low", "Close"])


def _fetch_equity_intraday_vap_profile(yf_symbol: str, bins: int = 24) -> dict[str, Any]:
    """
    Zero-API-key intraday Volume-at-Price (VAP) & Liquidity Profile for Equities / ETFs / FX.
    Computes Point of Control (POC), 70% Value Area (VAH / VAL), Intraday VWAP, and Directional Volume Imbalance.
    """
    import numpy as np
    import pandas as pd

    df = _download_yf_safe(yf_symbol, period="5d", interval="5m")
    last_close = float(df["Close"].iloc[-1])
    digits = _price_digits(last_close)

    # Latest session slice for intraday VWAP
    df_idx_dates = pd.to_datetime(df.index).date
    latest_date = df_idx_dates[-1]
    session_df = df.loc[df_idx_dates == latest_date]
    if session_df.empty:
        session_df = df.tail(78)

    typical_px = (session_df["High"] + session_df["Low"] + session_df["Close"]) / 3.0
    sess_vol = session_df["Volume"].astype(float)
    tot_sess_vol = float(sess_vol.sum())
    if tot_sess_vol > 0:
        intraday_vwap = float((typical_px * sess_vol).sum() / tot_sess_vol)
    else:
        intraday_vwap = float(typical_px.mean())

    vwap_dist_bps = ((last_close - intraday_vwap) / intraday_vwap * 10000.0) if intraday_vwap > 0 else 0.0

    # 5-day Volume-at-Price (VAP) histogram across `bins` price buckets
    tp_all = ((df["High"] + df["Low"] + df["Close"]) / 3.0).to_numpy(dtype=float)
    vol_all = df["Volume"].to_numpy(dtype=float)
    if float(vol_all.sum()) <= 0:
        # FX spot tickers on Yahoo sometimes report 0 tick volume; weight equally by bar range activity
        vol_all = np.maximum((df["High"] - df["Low"]).to_numpy(dtype=float), 1e-6)

    p_min, p_max = float(np.min(df["Low"])), float(np.max(df["High"]))
    if p_max <= p_min:
        p_max = p_min * 1.001

    edges = np.linspace(p_min, p_max, bins + 1)
    centers = 0.5 * (edges[:-1] + edges[1:])
    hist_vol = np.zeros(bins, dtype=float)
    bucket_idx = np.clip(np.digitize(tp_all, edges) - 1, 0, bins - 1)
    for b_i, v in zip(bucket_idx, vol_all):
        hist_vol[b_i] += v

    poc_idx = int(np.argmax(hist_vol))
    poc_price = float(centers[poc_idx])

    # Expand outward from POC until 70% of total volume is captured (Institutional Value Area)
    target_vol = 0.70 * float(hist_vol.sum())
    cum_vol = float(hist_vol[poc_idx])
    lo_i, hi_i = poc_idx, poc_idx
    while cum_vol < target_vol and (lo_i > 0 or hi_i < bins - 1):
        next_lo = hist_vol[lo_i - 1] if lo_i > 0 else -1.0
        next_hi = hist_vol[hi_i + 1] if hi_i < bins - 1 else -1.0
        if next_hi >= next_lo and hi_i < bins - 1:
            hi_i += 1
            cum_vol += float(hist_vol[hi_i])
        elif lo_i > 0:
            lo_i -= 1
            cum_vol += float(hist_vol[lo_i])
        else:
            break

    val_price = float(edges[lo_i])
    vah_price = float(edges[hi_i + 1])

    # Directional Bar Pressure (Close > Open vs Close < Open over trailing 24 five-minute bars = 2 hours)
    recent_bars = df.tail(24)
    r_vol = recent_bars["Volume"].to_numpy(dtype=float)
    if float(r_vol.sum()) <= 0:
        r_vol = np.ones(len(recent_bars), dtype=float)
    up_mask = (recent_bars["Close"] >= recent_bars["Open"]).to_numpy()
    up_vol = float(r_vol[up_mask].sum())
    dn_vol = float(r_vol[~up_mask].sum())
    tot_dir = up_vol + dn_vol
    flow_imb = (up_vol - dn_vol) / tot_dir if tot_dir > 0 else 0.0

    # Top high-volume nodes below & above current price act as structural support / resistance magnets
    below_nodes = [
        (float(centers[i]), float(hist_vol[i]))
        for i in range(bins)
        if centers[i] <= last_close and hist_vol[i] > 0
    ]
    above_nodes = [
        (float(centers[i]), float(hist_vol[i]))
        for i in range(bins)
        if centers[i] > last_close and hist_vol[i] > 0
    ]
    below_top = sorted(below_nodes, key=lambda x: x[1], reverse=True)[:3]
    above_top = sorted(above_nodes, key=lambda x: x[1], reverse=True)[:3]

    max_bin_vol = max(float(np.max(hist_vol)), 1e-9)
    vap_histogram = [
        {
            "price": _clean_float(float(centers[i]), digits),
            "volume": _clean_float(float(hist_vol[i]), 0),
            "pct_of_max": _clean_float(float(hist_vol[i]) / max_bin_vol * 100.0, 1),
            "is_poc": bool(i == poc_idx),
            "in_value_area": bool(lo_i <= i <= hi_i),
        }
        for i in range(bins - 1, -1, -1)
    ]

    moomoo_detected = check_tcp_port("127.0.0.1", 11111)

    return {
        "symbol": yf_symbol,
        "asset_class": "EQUITY_ETF_FX",
        "feed_type": "INTRADAY_5M_VOLUME_AT_PRICE_MICROSTRUCTURE",
        "exchange_source": "Yahoo Finance Zero-Auth 5m Intraday Profile",
        "timestamp_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "price_and_vwap": {
            "last_price": _clean_float(last_close, digits),
            "session_vwap": _clean_float(intraday_vwap, digits),
            "vwap_deviation_bps": _clean_float(vwap_dist_bps, 2),
            "position_vs_vwap": "ABOVE_SESSION_VWAP" if last_close >= intraday_vwap else "BELOW_SESSION_VWAP",
        },
        "volume_profile_5d": {
            "point_of_control_poc": _clean_float(poc_price, digits),
            "value_area_high_vah_70pct": _clean_float(vah_price, digits),
            "value_area_low_val_70pct": _clean_float(val_price, digits),
            "value_area_regime": (
                "ABOVE_VALUE_AREA_BREAKOUT"
                if last_close > vah_price
                else ("BELOW_VALUE_AREA_BREAKDOWN" if last_close < val_price else "INSIDE_70PCT_VALUE_AREA")
            ),
        },
        "intraday_flow_pressure": {
            "trailing_2h_volume_imbalance": _clean_float(flow_imb, 4),
            "schmitt_trigger_regime": (
                "INSTITUTIONAL_ACCUMULATION_BIAS"
                if flow_imb >= 0.20
                else ("INSTITUTIONAL_DISTRIBUTION_BIAS" if flow_imb <= -0.20 else "TWO_WAY_ROTATION_DEADZONE")
            ),
        },
        "high_volume_liquidity_nodes": {
            "support_nodes_below_price": [{"price": _clean_float(p, digits), "volume": _clean_float(v, 0)} for p, v in below_top],
            "resistance_nodes_above_price": [{"price": _clean_float(p, digits), "volume": _clean_float(v, 0)} for p, v in above_top],
        },
        "vap_histogram": vap_histogram,
        "nasdaq_totalview_60level_l2_bridge": {
            "local_moomoo_opend_port_11111": "DETECTED_ONLINE" if moomoo_detected else "NOT_DETECTED",
            "upgrade_note": (
                "For millisecond 60-level NASDAQ TotalView L2 Order Book, Spoofing Wall-Collapse & Iceberg detection "
                f"on US/HK/JP equities, unlock Lumina OrderBook MCP Pro via GitHub Sponsors ({SPONSOR_URL})."
            ),
        },
    }


def fetch_live_orderbook_or_vap(symbol: str = "BTC-USD", depth: int = 60) -> dict[str, Any]:
    """Unified entry point for Tool 1: Live 60-level L2 book (Crypto) or 5m VAP profile (Stocks/ETFs/FX)."""
    info = normalize_symbol_info(symbol)
    if info["asset_class"] == "CRYPTO":
        return _fetch_crypto_l2_multi_exchange(info["base"], depth=depth)
    return _fetch_equity_intraday_vap_profile(info["yf_symbol"])


def analyze_closed_bar_quant_packet(
    df: pd.DataFrame,
    symbol: str,
    timeframe: str,
    daily_df: pd.DataFrame | None = None,
    drop_unclosed_last_bar: bool = True,
) -> dict[str, Any]:
    """
    Pure deterministic Closed-Bar Quantitative & Risk Packet calculator.
    Eliminates mid-candle repainting and LLM arithmetic drift.
    """
    import numpy as np
    import pandas as pd

    if len(df) < 35:
        raise ValueError(f"Insufficient historical bars ({len(df)}) for {symbol} ({timeframe}).")

    # Drop the currently forming bar when >35 bars exist so signals never repaint mid-candle
    working = df.iloc[:-1].copy() if (drop_unclosed_last_bar and len(df) > 36) else df.copy()

    close = working["Close"].astype(float)
    high = working["High"].astype(float)
    low = working["Low"].astype(float)
    opn = working["Open"].astype(float)
    vol = working["Volume"].astype(float)

    c_now = float(close.iloc[-1])
    o_now = float(opn.iloc[-1])
    h_now = float(high.iloc[-1])
    l_now = float(low.iloc[-1])
    digits = _price_digits(c_now)

    ema20_s = close.ewm(span=20, adjust=False).mean()
    ema50_s = close.ewm(span=50, adjust=False).mean()
    ema200_s = close.ewm(span=200, adjust=False).mean()
    ema20 = float(ema20_s.iloc[-1])
    ema50 = float(ema50_s.iloc[-1])
    ema200 = float(ema200_s.iloc[-1])

    if c_now > ema20 > ema50 > ema200:
        ema_state = "BULLISH_TREND_STACK"
    elif c_now < ema20 < ema50 < ema200:
        ema_state = "BEARISH_TREND_STACK"
    else:
        ema_state = "MIXED_TRANSITION_STACK"

    # Wilder's RSI(14)
    delta = close.diff()
    gain = delta.clip(lower=0.0).ewm(alpha=1.0 / 14.0, adjust=False).mean()
    loss = (-delta.clip(upper=0.0)).ewm(alpha=1.0 / 14.0, adjust=False).mean()
    rs = float(gain.iloc[-1]) / max(float(loss.iloc[-1]), 1e-12)
    rsi14 = 100.0 - (100.0 / (1.0 + rs))

    # Wilder's ATR(14)
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low).abs(),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    atr14 = float(tr.ewm(alpha=1.0 / 14.0, adjust=False).mean().iloc[-1])
    atr_pct = (atr14 / c_now * 100.0) if c_now > 0 else 0.0

    # Relative Volume (RVOL vs trailing 20 closed bars excluding current; handle Yahoo 0-vol crypto bars)
    nonzero_vol = vol[vol > 0]
    if len(nonzero_vol) >= 5:
        curr_v = float(vol.iloc[-1]) if float(vol.iloc[-1]) > 0 else float(nonzero_vol.iloc[-1])
        base_slice = nonzero_vol.iloc[-21:-1] if len(nonzero_vol) >= 21 else nonzero_vol
        vol_baseline = float(base_slice.mean())
        rvol = (curr_v / vol_baseline) if vol_baseline > 0 else 1.0
    else:
        rvol = 1.0

    # Causal 15-day ADR Fuel & Weinstein 200-Day SMA Stage-2 Check (if daily_df supplied)
    stage2_status = "UNKNOWN"
    sma200_daily = None
    adr15_pct = None
    adr_fuel_remaining_pct = None
    if daily_df is not None and len(daily_df) >= 20:
        d_close = daily_df["Close"].astype(float)
        d_high = daily_df["High"].astype(float)
        d_low = daily_df["Low"].astype(float)
        d_open = daily_df["Open"].astype(float)

        if len(d_close) >= 200:
            sma200_daily = float(d_close.rolling(200).mean().iloc[-1])
            stage2_status = "ABOVE_200D_SMA_STAGE2" if c_now >= sma200_daily else "BELOW_200D_SMA_DEFENSIVE"

        # Strictly causal ADR15 using completed prior 15 sessions (shift(1) avoids look-ahead bias)
        prior_ranges_pct = ((d_high - d_low) / d_close.replace(0, np.nan) * 100.0).iloc[:-1].tail(15)
        if len(prior_ranges_pct) >= 5:
            adr15_pct = float(prior_ranges_pct.mean())
            today_used_pct = abs(c_now - float(d_open.iloc[-1])) / max(float(d_open.iloc[-1]), 1e-9) * 100.0
            if adr15_pct > 0:
                adr_fuel_remaining_pct = max(0.0, (1.0 - today_used_pct / adr15_pct) * 100.0)

    # Schmitt-Trigger Factor Ontology Labels (eliminates LLM polarity hallucinations)
    if rsi14 >= 72.0:
        rsi_label = "OVERBOUGHT_EXTENDED"
    elif rsi14 >= 55.0:
        rsi_label = "BULLISH_MOMENTUM_REGIME"
    elif rsi14 <= 28.0:
        rsi_label = "OVERSOLD_WASHOUT"
    elif rsi14 <= 45.0:
        rsi_label = "BEARISH_MOMENTUM_REGIME"
    else:
        rsi_label = "NEUTRAL_HYSTERESIS_DEADZONE"

    if rvol >= 1.8:
        rvol_label = "INSTITUTIONAL_VOLUME_EXPANSION"
    elif rvol <= 0.65:
        rvol_label = "THIN_ILLIQUID_PARTICIPATION"
    else:
        rvol_label = "NORMAL_PARTICIPATION"

    # Deterministic 1.5x ATR Stop Loss & 1.5R / 3.0R Structural Targets (Long & Short)
    stop_dist = max(1.5 * atr14, c_now * 0.0015)
    units_per_100usd_risk = 100.0 / stop_dist if stop_dist > 0 else 0.0

    bar_ts = str(working.index[-1])

    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "anti_repaint_guard": {
            "closed_bar_only": bool(drop_unclosed_last_bar),
            "confirmed_bar_timestamp": bar_ts,
        },
        "closed_candle": {
            "open": _clean_float(o_now, digits),
            "high": _clean_float(h_now, digits),
            "low": _clean_float(l_now, digits),
            "close": _clean_float(c_now, digits),
            "volume": _clean_float(float(vol.iloc[-1]), 2),
        },
        "trend_and_momentum": {
            "ema20": _clean_float(ema20, digits),
            "ema50": _clean_float(ema50, digits),
            "ema200": _clean_float(ema200, digits),
            "ema_alignment": ema_state,
            "daily_sma200": _clean_float(sma200_daily, digits) if sma200_daily is not None else None,
            "weinstein_regime": stage2_status,
            "rsi14": _clean_float(rsi14, 2),
            "rvol20": _clean_float(rvol, 2),
            "atr14": _clean_float(atr14, digits),
            "atr14_pct": _clean_float(atr_pct, 3),
            "causal_adr15_pct": _clean_float(adr15_pct, 2) if adr15_pct is not None else None,
            "intraday_adr_fuel_remaining_pct": (
                _clean_float(adr_fuel_remaining_pct, 1) if adr_fuel_remaining_pct is not None else None
            ),
        },
        "schmitt_trigger_ontology": {
            "momentum_polarity": rsi_label,
            "volume_participation": rvol_label,
            "chasing_exhaustion_warning": bool(
                adr_fuel_remaining_pct is not None and adr_fuel_remaining_pct < 18.0
            ),
        },
        "deterministic_risk_map": {
            "stop_distance_1_5_atr": _clean_float(stop_dist, digits),
            "position_units_per_100usd_risk": _clean_float(units_per_100usd_risk, 4),
            "long_blueprint": {
                "reference_entry": _clean_float(c_now, digits),
                "structural_stop_loss": _clean_float(c_now - stop_dist, digits),
                "target_1_5r_partial": _clean_float(c_now + 1.5 * stop_dist, digits),
                "target_3_0r_runner": _clean_float(c_now + 3.0 * stop_dist, digits),
            },
            "short_blueprint": {
                "reference_entry": _clean_float(c_now, digits),
                "structural_stop_loss": _clean_float(c_now + stop_dist, digits),
                "target_1_5r_partial": _clean_float(c_now - 1.5 * stop_dist, digits),
                "target_3_0r_runner": _clean_float(c_now - 3.0 * stop_dist, digits),
            },
        },
    }


def build_live_quant_candle_packet(
    symbol: str = "NVDA",
    timeframe: str = "1h",
    include_chart_bars: bool = False,
) -> dict[str, Any]:
    """Fetch bars for `symbol` and compute deterministic closed-bar quant & risk packet."""
    import pandas as pd

    info = normalize_symbol_info(symbol)
    yf_sym = info["yf_symbol"]

    tf_map = {
        "5m": ("5d", "5m"),
        "15m": ("15d", "15m"),
        "30m": ("30d", "30m"),
        "1h": ("60d", "60m"),
        "60m": ("60d", "60m"),
        "1d": ("2y", "1d"),
    }
    tf_key = timeframe.strip().lower()
    period, interval = tf_map.get(tf_key, ("60d", "60m"))

    df = _download_yf_safe(yf_sym, period=period, interval=interval)
    daily_df = df if interval == "1d" else _download_yf_safe(yf_sym, period="1y", interval="1d")

    pkt = analyze_closed_bar_quant_packet(
        df=df,
        symbol=yf_sym,
        timeframe=tf_key if tf_key in tf_map else "1h",
        daily_df=daily_df,
        drop_unclosed_last_bar=True,
    )

    if include_chart_bars:
        full_closed = df.iloc[:-1].copy() if len(df) > 36 else df.copy()
        c_full = full_closed["Close"].astype(float)
        e20_full = c_full.ewm(span=20, adjust=False).mean()
        e50_full = c_full.ewm(span=50, adjust=False).mean()
        e200_full = c_full.ewm(span=200, adjust=False).mean()
        working = full_closed.tail(150)
        e20 = e20_full.loc[working.index]
        e50 = e50_full.loc[working.index]
        e200 = e200_full.loc[working.index]
        digits = _price_digits(float(c_full.iloc[-1]))

        bars_out: list[dict[str, Any]] = []
        seen_ts: set[int] = set()
        for ts, row in working.iterrows():
            ts_dt = pd.Timestamp(ts)
            if ts_dt.tzinfo is None:
                unix_s = int(ts_dt.tz_localize("UTC").timestamp())
            else:
                unix_s = int(ts_dt.tz_convert("UTC").timestamp())
            if unix_s in seen_ts:
                continue
            seen_ts.add(unix_s)
            bars_out.append(
                {
                    "time": unix_s,
                    "open": _clean_float(row["Open"], digits),
                    "high": _clean_float(row["High"], digits),
                    "low": _clean_float(row["Low"], digits),
                    "close": _clean_float(row["Close"], digits),
                    "volume": _clean_float(row["Volume"], 2),
                    "ema20": _clean_float(e20.loc[ts], digits),
                    "ema50": _clean_float(e50.loc[ts], digits),
                    "ema200": _clean_float(e200.loc[ts], digits),
                }
            )
        bars_out.sort(key=lambda x: x["time"])
        pkt["chart_bars"] = bars_out

    return pkt


def scan_multi_asset_anomalies(symbols_csv: str = "BTC-USD,ETH-USD,SOL-USD,NVDA,TSLA,GLD") -> dict[str, Any]:
    """Scan up to 10 symbols in one shot and rank them by absolute order-flow / volume pressure."""
    raw_list = [s.strip() for s in symbols_csv.split(",") if s.strip()][:10]
    results: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []

    for sym in raw_list:
        try:
            ob = fetch_live_orderbook_or_vap(sym, depth=40)
            if ob["asset_class"] == "CRYPTO":
                pressure = float(ob["order_flow_imbalance"]["distance_weighted_pressure"])
                regime = ob["order_flow_imbalance"]["schmitt_trigger_regime"]
                px = ob["touch"]["mid_price"]
                spread_bps = ob["touch"]["spread_bps"]
            else:
                pressure = float(ob["intraday_flow_pressure"]["trailing_2h_volume_imbalance"])
                regime = ob["intraday_flow_pressure"]["schmitt_trigger_regime"]
                px = ob["price_and_vwap"]["last_price"]
                spread_bps = None

            results.append(
                {
                    "symbol": ob["symbol"],
                    "asset_class": ob["asset_class"],
                    "feed_type": ob["feed_type"],
                    "price": px,
                    "spread_bps": spread_bps,
                    "microstructure_pressure_score": _clean_float(pressure, 4),
                    "abs_conviction": _clean_float(abs(pressure), 4),
                    "schmitt_trigger_regime": regime,
                }
            )
        except Exception as exc:
            errors.append({"symbol": sym, "error": str(exc)})

    results.sort(key=lambda r: r["abs_conviction"], reverse=True)
    return {
        "scanned_count": len(results),
        "timestamp_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "ranked_opportunities": results,
        "skipped_symbols": errors,
    }
