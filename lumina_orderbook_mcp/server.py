"""
Lumina OrderBook & Quantitative Microstructure MCP Server (`lumina-orderbook-mcp`).

Compatible with both MCP Python SDK v2 (`MCPServer`) and v1 (`FastMCP`).
Works out-of-the-box in Claude Code, Cursor, Claude Desktop, Windsurf, and Antigravity
with ZERO API keys required.
"""

from __future__ import annotations

import json
import os
import pathlib
import shutil
import sys
from typing import Any

try:
    from mcp.server.mcpserver import MCPServer as _CompatMCPServer
except ImportError:
    from mcp.server.fastmcp import FastMCP as _CompatMCPServer  # type: ignore[no-redef]

from .core_engine import (
    build_live_quant_candle_packet,
    check_local_institutional_ports,
    fetch_live_orderbook_or_vap,
    scan_multi_asset_anomalies,
)

mcp = _CompatMCPServer(
    "lumina-orderbook-mcp",
    instructions=(
        "Deterministic Market Microstructure, 60-Level L2 Order Book Imbalance (OFI), "
        "Volume-at-Price (POC/VAH/VAL), Schmitt-Trigger Factor Ontology, and Closed-Bar ATR Risk Maps. "
        "Always anchor financial analysis on the exact numbers returned by these tools rather than "
        "estimating prices, spreads, or R-multiples in prose."
    ),
)


def _to_json_str(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=False)


@mcp.tool()
def get_live_l2_orderbook(symbol: str = "BTC-USD", depth: int = 60) -> str:
    """
    Fetch real-time market microstructure & liquidity walls for Crypto, US/JP Stocks, ETFs, Gold, or FX.

    - For Crypto (e.g. 'BTC-USD', 'ETH-USD', 'SOL-USD', 'XRP-USD'):
      Returns live 60-level L2 limit order book (Coinbase -> Kraken -> Hyperliquid automatic fallback),
      Stoikov micro-price, spread (bps), Top-10 & Deep-60 Order Flow Imbalance (OFI), largest Bid/Ask
      liquidity walls in USD, and recent aggressive tape delta.
    - For Stocks / ETFs / Gold / FX (e.g. 'NVDA', 'TSLA', 'SPY', 'GLD', '7203.T', 'USDJPY'):
      Returns live 5-minute Volume-at-Price (VAP) Point of Control (POC), 70% Value Area (VAH/VAL),
      Session VWAP deviation (bps), institutional accumulation/distribution pressure, and local
      Moomoo OpenD (:11111) NASDAQ TotalView port readiness.
    """
    try:
        data = fetch_live_orderbook_or_vap(symbol=symbol, depth=depth)
        return _to_json_str(data)
    except Exception as exc:
        return _to_json_str({"error": str(exc), "symbol": symbol})


@mcp.tool()
def get_ai_quant_candle_packet(symbol: str = "NVDA", timeframe: str = "1h") -> str:
    """
    Compute a zero-repaint (closed-bar only) quantitative analysis & deterministic ATR risk packet.

    Supported timeframes: '5m', '15m', '30m', '1h', '1d'.
    Works across US Stocks ('NVDA', 'AAPL'), Japanese Stocks ('7203.T', '8035.T'),
    Crypto ('BTC-USD', 'SOL-USD'), Commodities ('GLD', 'XAUUSD'), and FX ('USDJPY').

    Returns:
      - Confirmed closed candle OHLCV (eliminates mid-candle repainting)
      - EMA(20/50/200) alignment + Weinstein 200-Day SMA Stage-2 regime
      - Causal 15-day ADR% & remaining intraday ADR fuel% (chasing-exhaustion warning)
      - Schmitt-Trigger Factor Ontology semantic polarity tags (prevents LLM polarity hallucinations)
      - Deterministic 1.5x ATR structural stop loss, 1.5R partial & 3.0R runner targets, and unit sizing per $100 risk.
    """
    try:
        data = build_live_quant_candle_packet(symbol=symbol, timeframe=timeframe)
        return _to_json_str(data)
    except Exception as exc:
        return _to_json_str({"error": str(exc), "symbol": symbol, "timeframe": timeframe})


@mcp.tool()
def scan_market_liquidity_anomalies(
    symbols_csv: str = "BTC-USD,ETH-USD,SOL-USD,NVDA,TSLA,GLD",
) -> str:
    """
    Scan up to 10 comma-separated tickers simultaneously and rank them by real-time
    L2 order-book pressure or intraday institutional volume imbalance.
    """
    try:
        data = scan_multi_asset_anomalies(symbols_csv=symbols_csv)
        return _to_json_str(data)
    except Exception as exc:
        return _to_json_str({"error": str(exc), "symbols_csv": symbols_csv})


@mcp.tool()
def check_pro_institutional_bridge() -> str:
    """
    Check localhost (127.0.0.1) readiness for institutional Level-2 / execution bridges
    (Moomoo OpenD :11111 NASDAQ TotalView 60-depth, Interactive Brokers Gateway/TWS :4002/:7497,
    and MetaTrader 5 RPyC Bridge :8001) and display Lumina OrderBook MCP Pro upgrade details.
    """
    return _to_json_str(check_local_institutional_ports())


def install_claude_desktop_config() -> list[str]:
    """
    Auto-detect and safely register `lumina-orderbook` in Claude Desktop config files
    across Windows (both Standard `%APPDATA%\\Claude` and Microsoft Store `Claude-Data`),
    macOS (`~/Library/Application Support/Claude`), and Linux (`~/.config/Claude`).
    """
    targets: list[pathlib.Path] = []
    if sys.platform == "win32":
        local_app = os.environ.get("LOCALAPPDATA", "")
        roaming_app = os.environ.get("APPDATA", "")
        if local_app:
            claude_data = pathlib.Path(local_app) / "Claude-Data"
            if claude_data.exists():
                targets.extend(claude_data.glob("claude_*/claude_desktop_config.json"))
            msix_pkgs = pathlib.Path(local_app) / "Packages"
            if msix_pkgs.exists():
                for pkg in msix_pkgs.glob("Claude_*"):
                    cand = pkg / "LocalCache" / "Roaming" / "Claude" / "claude_desktop_config.json"
                    if cand.exists():
                        targets.append(cand)
        if roaming_app and not targets:
            targets.append(pathlib.Path(roaming_app) / "Claude" / "claude_desktop_config.json")
    elif sys.platform == "darwin":
        targets.append(pathlib.Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json")
    else:
        targets.append(pathlib.Path.home() / ".config" / "Claude" / "claude_desktop_config.json")

    updated: list[str] = []
    for cfg in targets:
        cfg.parent.mkdir(parents=True, exist_ok=True)
        if cfg.exists():
            shutil.copy2(cfg, cfg.with_suffix(".json.bak"))
            try:
                content = cfg.read_text(encoding="utf-8").strip()
                data = json.loads(content) if content else {}
            except Exception:
                data = {}
        else:
            data = {}

        data.setdefault("mcpServers", {})["lumina-orderbook"] = {
            "command": sys.executable,
            "args": ["-m", "lumina_orderbook_mcp.server"],
        }
        cfg.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        updated.append(str(cfg))
    return updated


def main() -> None:
    """CLI entry point for `lumina-orderbook-mcp` (stdio transport or `--install-claude`)."""
    if "--install-claude" in sys.argv:
        paths = install_claude_desktop_config()
        print("Successfully registered `lumina-orderbook` in Claude Desktop:")
        for p in paths:
            print(f"  -> {p}")
        print("Please fully quit Claude Desktop (File -> Quit / Ctrl+Q) and reopen it.")
        return
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
