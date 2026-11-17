"""Offline & deterministic protocol test suite for `lumina-orderbook-mcp`."""

from __future__ import annotations

import json
import math

import numpy as np
import pandas as pd
import pytest

from lumina_orderbook_mcp.core_engine import (
    analyze_closed_bar_quant_packet,
    analyze_l2_book_arrays,
    check_local_institutional_ports,
    normalize_symbol_info,
)
from lumina_orderbook_mcp.server import check_pro_institutional_bridge, mcp


def test_symbol_normalization() -> None:
    assert normalize_symbol_info("btc")["asset_class"] == "CRYPTO"
    assert normalize_symbol_info("ETH-USD")["yf_symbol"] == "ETH-USD"
    assert normalize_symbol_info("SOLUSDT")["base"] == "SOL"
    assert normalize_symbol_info("NVDA")["asset_class"] == "EQUITY_ETF_FX"
    assert normalize_symbol_info("7203.T")["yf_symbol"] == "7203.T"
    assert normalize_symbol_info("XAUUSD")["yf_symbol"] == "GC=F"


def test_l2_orderbook_imbalance_and_walls_deterministic() -> None:
    # Strong bid dominance book (60 levels)
    bids = [(100000.0 - i * 10.0, 2.5 if i != 3 else 40.0) for i in range(60)]
    asks = [(100010.0 + i * 10.0, 0.8 if i != 5 else 12.0) for i in range(60)]
    trades = [
        {"price": 100010.0, "size": 3.2, "aggressor": "BUY"},
        {"price": 100000.0, "size": 0.5, "aggressor": "SELL"},
    ]

    res = analyze_l2_book_arrays(bids, asks, depth=60, recent_trades=trades)
    assert res["levels_analyzed"] == {"bids": 60, "asks": 60}
    assert res["touch"]["best_bid"] == 100000.0
    assert res["touch"]["best_ask"] == 100010.0
    assert res["touch"]["spread_abs"] == 10.0
    assert res["order_flow_imbalance"]["top10_imbalance"] > 0.35
    assert res["order_flow_imbalance"]["schmitt_trigger_regime"] == "STRONG_BID_DOMINANCE"
    assert res["liquidity_walls"]["largest_bid_support_walls"][0]["price"] == 99970.0
    assert res["liquidity_walls"]["largest_ask_resistance_walls"][0]["price"] == 100060.0
    assert res["recent_tape_flow"]["tape_state"] == "AGGRESSIVE_TAPE_BUYING"


def test_closed_bar_anti_repaint_and_risk_map_invariants() -> None:
    idx = pd.date_range("2026-01-01", periods=250, freq="D")
    prices = np.linspace(100.0, 180.0, 250)
    df = pd.DataFrame(
        {
            "Open": prices - 0.8,
            "High": prices + 2.0,
            "Low": prices - 2.0,
            "Close": prices,
            "Volume": np.full(250, 1_500_000.0),
        },
        index=idx,
    )
    # Corrupt the very last unclosed forming candle with an extreme spike to verify anti-repaint slicing!
    df.iloc[-1, df.columns.get_loc("Close")] = 9999.0

    pkt = analyze_closed_bar_quant_packet(
        df=df,
        symbol="NVDA",
        timeframe="1d",
        daily_df=df.iloc[:-1],
        drop_unclosed_last_bar=True,
    )
    # Confirmed bar must be the 249th bar (not the unclosed 9999.0 spike!)
    assert pkt["anti_repaint_guard"]["closed_bar_only"] is True
    assert pkt["closed_candle"]["close"] < 200.0
    assert pkt["trend_and_momentum"]["ema_alignment"] == "BULLISH_TREND_STACK"

    long_bp = pkt["deterministic_risk_map"]["long_blueprint"]
    short_bp = pkt["deterministic_risk_map"]["short_blueprint"]
    assert long_bp["structural_stop_loss"] < long_bp["reference_entry"] < long_bp["target_1_5r_partial"] < long_bp["target_3_0r_runner"]
    assert short_bp["structural_stop_loss"] > short_bp["reference_entry"] > short_bp["target_1_5r_partial"] > short_bp["target_3_0r_runner"]

    # Verify strict JSON serializability & zero NaN/Inf
    dumped = json.dumps(pkt)
    assert "NaN" not in dumped and "Infinity" not in dumped


def test_mcp_server_tools_registered() -> None:
    bridge_json = json.loads(check_pro_institutional_bridge())
    assert "localhost_gateways" in bridge_json
    assert "https://github.com/sponsors/ramuza0113-sketch" in bridge_json["pro_tier_capabilities"]["sponsor_url"]
    assert mcp.name == "lumina-orderbook-mcp"


def test_stdio_jsonrpc_wire_handshake() -> None:
    import asyncio
    import os
    import pathlib
    import sys

    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    repo_root = str(pathlib.Path(__file__).resolve().parents[1])

    async def _wire_check() -> None:
        env = dict(os.environ)
        env["PYTHONPATH"] = repo_root
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "lumina_orderbook_mcp.server"],
            env=env,
        )
        async with stdio_client(params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                tools_resp = await session.list_tools()
                names = {t.name for t in tools_resp.tools}
                assert {
                    "get_live_l2_orderbook",
                    "get_ai_quant_candle_packet",
                    "scan_market_liquidity_anomalies",
                    "open_live_quant_terminal",
                    "check_pro_institutional_bridge",
                }.issubset(names)
                call_resp = await session.call_tool("check_pro_institutional_bridge", {})
                payload = json.loads(call_resp.content[0].text)
                assert payload["edition"].startswith("Open-Source")

    asyncio.run(_wire_check())


def test_live_terminal_http_server() -> None:
    import urllib.request
    from lumina_orderbook_mcp.dashboard import launch_live_terminal

    info = launch_live_terminal(symbol="BTC-USD", open_browser=False)
    assert info["status"] == "LIVE_TERMINAL_RUNNING"
    html = urllib.request.urlopen(info["terminal_url"], timeout=3).read().decode("utf-8")
    assert "LUMINA ORDERBOOK & QUANT RISK TERMINAL" in html


