<div align="center">

# 📊 Lumina OrderBook MCP (`lumina-orderbook-mcp`)

**Give Claude Code, Cursor, and AI Agents Real-Time 60-Level L2 Order Books, Liquidity Walls, Schmitt-Trigger Factor Ontology & Zero-Repaint ATR Risk Maps — With Zero API Keys.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-brightgreen.svg)](https://www.python.org/)
[![MCP Compatible](https://img.shields.io/badge/MCP-v1%20%26%20v2%20Compatible-7C3AED.svg)](https://modelcontextprotocol.io)
[![DOI Paper 1](https://img.shields.io/badge/Zenodo%20DOI-10.5281%2Fzenodo.23935930-007EC6.svg?logo=zenodo&logoColor=white)](https://doi.org/10.5281/zenodo.23935930)
[![DOI Paper 4](https://img.shields.io/badge/Zenodo%20DOI-10.5281%2Fzenodo.24050440-007EC6.svg?logo=zenodo&logoColor=white)](https://doi.org/10.5281/zenodo.24050440)
[![Featured Ecosystem](https://awesome.re/mentioned-badge.svg)](https://github.com/ramuza0113-sketch/lumina-ai-hedge-fund)
[![GitHub Sponsors](https://img.shields.io/badge/Sponsor-Unlock%20Pro%20L2%20Sentinel-EA4AAA?logo=githubsponsors&logoColor=white)](https://github.com/sponsors/ramuza0113-sketch)

[⚡ 30-Second AI Copy-Paste Install](#-30-second-setup-just-paste-1-sentence-into-your-ai) • [🛠️ MCP Tools](#️-included-mcp-tools) • [📦 Sample Output](#-real-deterministic-json-output) • [💎 Pro Edition (NASDAQ TotalView 60-Depth)](#-community-free-vs-sponsor-pro-edition) • [🇯🇵 日本語ガイド](#-日本語クイックガイド-japanese)

</div>

---

## Why `lumina-orderbook-mcp`?

> *"LLM nodes should argue about meaning; deterministic code should own the numbers."*

When people ask an LLM *"Is NVDA or BTC a good entry right now?"*, standard chatbots either hallucinate prices, eyeball screenshots, repaint on unclosed candles, or drift on stop-loss arithmetic. And existing TradingView MCP scrapers require keeping a heavy desktop app open on a debug port.

**`lumina-orderbook-mcp`** runs 100% locally on your machine with **zero API keys, zero account signups, and zero TradingView Desktop dependency**:

1. **Live 60-Level L2 Limit Order Book & Tape Imbalance (24/7 Crypto)**: Multi-exchange automatic failover (`Coinbase Exchange` $\rightarrow$ `Kraken` $\rightarrow$ `Hyperliquid` — never geo-blocked by HTTP 451 in the US, EU, or Japan). Computes Stoikov micro-price, spread (bps), Top-10 & Deep-60 Order Flow Imbalance (OFI), largest USD buy/sell walls, and aggressive tape delta.
2. **Intraday 5m Volume-at-Price (VAP) Microstructure (US/JP Equities, ETFs, Gold, FX)**: Computes Point of Control (`POC`), 70% Institutional Value Area (`VAH` / `VAL`), Session `VWAP` deviation in bps, and high-volume support/resistance magnets (`NVDA`, `TSLA`, `SPY`, `GLD`, `7203.T`, `USDJPY`, `XAUUSD`).
3. **Zero-Repaint Closed-Bar Risk Blueprint**: Automatically slices off unclosed forming candles so signals never repaint mid-bar. Outputs `EMA(20/50/200)`, Weinstein `200-Day SMA` Stage-2 status, causal `ADR(15)` remaining intraday fuel %, **Schmitt-Trigger Factor Ontology** polarity tags, and exact `1.5x ATR` structural stop / `1.5R` & `3.0R` targets.

---

## ⚡ 30-Second Setup (Just Paste 1 Sentence into Your AI)

**No manual JSON editing needed.** Copy and paste this single sentence into **Claude Code**, **Cursor**, **Windsurf**, or **Antigravity**:

```text
Please install and configure the MCP server from https://github.com/ramuza0113-sketch/lumina-orderbook-mcp so you can query live L2 order books, OFI liquidity walls, and deterministic ATR risk maps.
```

### Or Configure Directly via CLI / JSON

#### Option A: Claude Code (1 command with `uvx`)
```bash
claude mcp add lumina-orderbook -- uvx --from git+https://github.com/ramuza0113-sketch/lumina-orderbook-mcp lumina-orderbook-mcp
```

#### Option B: Cursor (`.cursor/mcp.json`) / Claude Desktop (`claude_desktop_config.json`)
```json
{
  "mcpServers": {
    "lumina-orderbook": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/ramuza0113-sketch/lumina-orderbook-mcp",
        "lumina-orderbook-mcp"
      ]
    }
  }
}
```

#### Option C: Standard `pip` Install (Without `uv`)
```bash
pip install git+https://github.com/ramuza0113-sketch/lumina-orderbook-mcp.git
```
Then set `"command": "lumina-orderbook-mcp"` and `"args": []` in your MCP client config.

---

## 🛠️ Included MCP Tools

| Tool Name | What It Computes Deterministically | Example Symbols |
| :--- | :--- | :--- |
| `get_live_l2_orderbook` | **Crypto**: Live 60-level L2 Order Book, Stoikov Micro-Price, Top-10 & Deep-60 OFI, Top-3 USD Bid/Ask Walls, Aggressive Tape Delta.<br>**Stocks/ETFs/FX**: 5m Volume-at-Price (`POC`, `VAH`, `VAL`), Session `VWAP` distance (bps), High-Volume Support/Resistance Nodes. | `BTC-USD`, `ETH-USD`, `SOL-USD`, `NVDA`, `TSLA`, `SPY`, `GLD`, `7203.T`, `XAUUSD` |
| `get_ai_quant_candle_packet` | **Closed-Bar Only** (anti-repaint) `EMA(20/50/200)`, Daily `SMA200` Stage-2 filter, `RSI(14)`, `RVOL(20)`, Causal `ADR(15)` remaining fuel %, Schmitt-Trigger Ontology tags, and `1.5x ATR` Stop / `1.5R` / `3.0R` Long & Short risk maps + unit sizing per `$100` risk. | `NVDA` (`1h`), `BTC-USD` (`15m`), `7203.T` (`1d`), `USDJPY` (`30m`) |
| `scan_market_liquidity_anomalies` | Scans up to 10 tickers in parallel/batch and ranks them by absolute microstructure order-flow / institutional volume conviction. | `"BTC-USD,ETH-USD,SOL-USD,NVDA,TSLA,GLD"` |
| `check_pro_institutional_bridge` | Localhost (`127.0.0.1`) TCP readiness check for Moomoo OpenD (`:11111` NASDAQ TotalView), IBKR Gateway/TWS (`:4002`/`:7497`), and MT5 Bridge (`:8001`). | *(No arguments needed)* |

### 💬 Prompts to Try Right Away
- *"Check the live 60-level L2 order book on `BTC-USD` and `ETH-USD`. Where are the biggest USD buy/sell walls right now, and is aggressive tape buying confirming the book?"*
- *"Pull both the intraday VAP liquidity profile and the 1h closed-bar quant risk packet for `NVDA`. Does it still have intraday ADR15 fuel left, and what are the exact 1.5R / 3.0R levels?"*
- *"Scan `BTC-USD,SOL-USD,NVDA,TSLA,SPY,GLD` and tell me which asset has the strongest institutional order-flow imbalance right now."*

---

## 📦 Real Deterministic JSON Output

```json
{
  "symbol": "BTC-USD",
  "asset_class": "CRYPTO",
  "feed_type": "LIVE_L2_LIMIT_ORDER_BOOK",
  "exchange_source": "Coinbase Exchange (Zero-Auth L2)",
  "levels_analyzed": { "bids": 60, "asks": 60 },
  "touch": {
    "best_bid": 64349.68,
    "best_ask": 64349.69,
    "stoikov_micro_price": 64349.69,
    "spread_abs": 0.01,
    "spread_bps": 0.0
  },
  "order_flow_imbalance": {
    "top10_bid_ratio_pct": 96.27,
    "top10_imbalance": 0.9255,
    "deep_imbalance": 0.4447,
    "distance_weighted_pressure": 0.7875,
    "schmitt_trigger_regime": "STRONG_BID_DOMINANCE"
  },
  "liquidity_walls": {
    "largest_bid_support_walls": [
      { "price": 64340.6, "size": 0.924096, "notional_usd": 59456.89, "distance_bps": 1.41 }
    ],
    "largest_ask_resistance_walls": [
      { "price": 64359.4, "size": 0.559841, "notional_usd": 36031.01, "distance_bps": 1.51 }
    ]
  },
  "recent_tape_flow": {
    "sample_trades": 60,
    "tape_delta_imbalance": 1.0,
    "tape_state": "AGGRESSIVE_TAPE_BUYING"
  }
}
```

---

## 💎 Community (Free) vs Sponsor Pro Edition

`lumina-orderbook-mcp` is part of the **[Lumina Quantitative Research Ecosystem](https://github.com/ramuza0113-sketch/lumina-ai-hedge-fund)** (featured in **[awesome-quant](https://github.com/wilsonfreitas/awesome-quant#trading--backtesting)** & **[Awesome_AI4Finance](https://github.com/AI4Finance-Foundation/Awesome_AI4Finance)**).

| Feature | Community Edition (This Repo — MIT) | 💎 Sponsor Pro Edition (`$25/mo` & `$100/mo`) |
| :--- | :---: | :---: |
| **API Keys Required** | **0 (Instant Run)** | Local BYOD (`Moomoo OpenD` / `IBKR` / `MT5`) |
| **Crypto 60-Level L2 Order Book + Tape OFI** | ✅ Included | ✅ Included + Multi-Venue Lead-Lag |
| **US/JP Stock 5m Volume-at-Price (`POC`/`VAH`/`VAL`)** | ✅ Included | ✅ Included |
| **Closed-Bar Schmitt-Trigger & ATR `1.5R/3.0R` Map** | ✅ Included | ✅ Included |
| **Live 60-Level US Equity L2 (`NASDAQ TotalView` via OpenD `:11111`)** | Port Readiness Check | ✅ **Full Millisecond 60-Depth Feed** |
| **Spoofing Wall-Collapse & Iceberg Absorption Detector** | — | ✅ **Scroll-Out Resistant Deep OFI (`DOI: 10.5281/zenodo.23935930`)** |
| **Z3 Theorem-Proved Slippage-Proof Pyramiding & OCO Bridge** | — | ✅ **Included (`$100/mo` Pro Container Tier)** |

👉 **[Become a GitHub Sponsor (`♡ Sponsor`) to support open-source quantitative research & unlock Sponsor-Only Pro repositories!](https://github.com/sponsors/ramuza0113-sketch)**

---

## 🇯🇵 日本語クイックガイド (Japanese)

**APIキー登録ゼロ・完全無料（MITライセンス）**で、お使いの **Claude Code / Cursor / Claude Desktop / Antigravity** に「リアルタイム60段板（暗号資産L2フル板）・機関投資家の売買壁・日米株の価格帯別出来高（POC/VAH/VAL）・確定足ベースのATR損切り＆利確マップ」を直結できるMCPサーバーです。

### 初心者向け：AIに「1行コピペ」するだけで自動導入
難しい設定ファイルの編集は不要です。普段使っている Claude Code や Cursor のチャット欄に、以下の1文をそのまま貼り付けて送信してください：

```text
https://github.com/ramuza0113-sketch/lumina-orderbook-mcp のMCPサーバーをインストールして設定に追加して。リアルタイムの板情報（OFI）とATRリスク計算を使えるようにして。
```

### 導入後にそのまま聞ける質問例
- `BTC-USD と ETH-USD のリアルタイム60段板を見て、今どこに一番厚い買い壁・売り壁があるか教えて`
- `NVDA と トヨタ(7203.T) の出来高プロファイル(POC)と1時間足の確定足リスクマップを出して。今日のADR値幅燃料はまだ残ってる？`
- `BTC-USD, SOL-USD, NVDA, TSLA, GLD を一括スキャンして、今一番板と出来高の偏りが強い銘柄をランキングして`

さらに米国株の **Moomoo OpenD（NASDAQ TotalView 60段リアルタイム板・見せ板スプーフィング急キャンセル検知・アイスバーグ吸収検知）** や上位コンテナを利用したい方は、右上の **[♡ Sponsor（GitHub Sponsors）](https://github.com/sponsors/ramuza0113-sketch)** から公式サポーター枠をご確認ください。

---

## 📚 Academic References & Citation

- **Hashimoto, K. (2026a)**. *Eliminating Polarity Hallucinations and Order Book Horizon Truncation Bias in Autonomous Multi-Agent Quantitative Systems: Schmitt-Trigger Factor Ontologies, Scroll-Out Resistant Deep OFI, and Slippage-Proof Pyramiding*. CERN Zenodo. DOI: [10.5281/zenodo.23935930](https://doi.org/10.5281/zenodo.23935930)
- **Hashimoto, K. (2026d)**. *Formal Verification of Quantitative Execution Guardrails via Z3 SMT Theorem Proving*. CERN Zenodo. DOI: [10.5281/zenodo.24050440](https://doi.org/10.5281/zenodo.24050440)
- **Main Multi-Agent Research Framework**: [`ramuza0113-sketch/lumina-ai-hedge-fund`](https://github.com/ramuza0113-sketch/lumina-ai-hedge-fund)

> **Disclaimer**: This software is provided strictly for quantitative research, educational, and informational purposes. Nothing output by this MCP server constitutes financial, investment, or trading advice.
