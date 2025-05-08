# app/tools/finance_tools.py

import json
import logging
import re
from datetime import datetime, timezone
from typing import Dict, List, Sequence

import yfinance as yf
from langchain_core.tools import tool
from langchain_community.tools.yahoo_finance_news import YahooFinanceNewsTool

from app.config import get_llm

LOGGER = logging.getLogger(__name__)
_LLM = get_llm()


# internal helpers
def _normalise_tickers(raw: str | Sequence[str]) -> List[str]:
    """
    Accept "MSFT, NVDA" | "MSFT NVDA" | ["MSFT","NVDA"]  → ["MSFT","NVDA"].
    """
    if isinstance(raw, str):
        tickers = re.split(r"[,\s]+", raw.strip())
    else:
        tickers = list(raw)
    return [t.upper() for t in tickers if t]


def _get_ticker_data(ticker: str) -> Dict:
    """
    Return a single compact dict with the most‑recent quote and key stats
    for *ticker*.  Uses `fast_info` when complete, otherwise falls back
    to the latest intraday bar so the function never breaks on thin symbols.
    """
    tk = yf.Ticker(ticker)
    fi = getattr(tk, "fast_info", {}) or {}

    price = fi.get("last_price")
    prev = fi.get("previous_close")
    ts = fi.get("last_timestamp")

    # ── Fallback when fast_info is missing any of the critical fields ───
    if price is None or ts is None or prev is None:
        hist = tk.history(period="1d", interval="1m")
        if hist.empty:
            raise RuntimeError(f"No price data available for {ticker}")
        latest = hist.iloc[-1]
        price = float(latest["Close"])
        prev = float(hist["Close"].iloc[0])  # 1st bar of the session
        ts = latest.name.to_pydatetime().timestamp()

    change = round(price - prev, 2)
    pct = round(100 * change / prev, 2) if prev else None

    return {
        "ticker": ticker.upper(),
        "price": round(price, 2),
        "currency": fi.get("currency"),
        "change": change,  # absolute Δ
        "percent": pct,  # % Δ
        "pe": fi.get("trailing_pe"),
        "fwd_pe": fi.get("forward_pe"),
        "week52_low": fi.get("year_low"),
        "week52_high": fi.get("year_high"),
        "timestamp_utc": datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(),
    }


# ──────────────────────────────────────────────────────────────────────────────
# LangGraph tools
# ──────────────────────────────────────────────────────────────────────────────
@tool
def yf_latest_price(
    tickers: str | List[str],
    fields: str | None = None,
    pretty: bool = True,
) -> str:
    """
    Live quote(s) and key stats for one or more tickers.

    Args
    ----
    tickers   Space/comma‑separated symbols or a list.   "MSFT, TSLA"
    fields    Optional comma list of fields to INCLUDE (e.g. "price,change,percent").
              The table will still show Price/Δ/%.
    pretty    If True, return a Markdown table + JSON; if False, JSON only.

    Returns
    -------
    str   Markdown table (optional) followed by JSON.
    """
    wanted = {f.strip() for f in fields.split(",")} if fields else None
    rows: list[dict] = []

    for tkr in _normalise_tickers(tickers):
        try:
            data = _get_ticker_data(tkr)
        except Exception as exc:
            data = {"ticker": tkr, "error": str(exc)}

        if wanted and "error" not in data:
            data = {k: v for k, v in data.items() if k in wanted or k == "ticker"}
        rows.append(data)

    # ---------- plain JSON for the model / callers ---------------------
    payload = json.dumps(rows, indent=2)

    if not pretty:
        return payload

    # ---------- human‑friendly Markdown table --------------------------
    def _fmt(v):  # tiny helper
        return f"{v:.2f}" if isinstance(v, (int, float)) else (v or "-")

    header = (
        "| Ticker | Price | Δ | % | 52‑wk Low | 52‑wk High | P/E | Fwd P/E |\n"
        "|:------:|------:|---:|--:|----------:|-----------:|----:|--------:|"
    )
    body_lines = []
    for d in rows:
        if "error" in d:
            body_lines.append(f"| {d['ticker']} | ‑ | ‑ | ‑ | ‑ | ‑ | ‑ | ‑ |")
            continue
        body_lines.append(
            "| {ticker} | {price:.2f} | {change:+.2f} | {percent:+.2f}% | "
            "{week52_low:.2f} | {week52_high:.2f} | {pe} | {fwd_pe} |".format(
                **{k: _fmt(v) for k, v in d.items()}
            )
        )
    markdown_table = "\n".join([header] + body_lines)

    return markdown_table + "\n\n```json\n" + payload + "\n```"


@tool
def yf_news(ticker: str, summarise: bool = True) -> str:
    """
    ➜ Latest Yahoo‑Finance headlines for *ticker* (max 10).

    Args:
      ticker: Stock symbol (e.g. "AAPL").
      summarise:  If True, add a 1‑sentence LLM summary per item.

    Returns:
      JSON string: {
         "ticker": "AAPL",
         "news": [ { title, body, summary? }, … ]
      }
    """
    raw = YahooFinanceNewsTool().invoke({"query": ticker})

    if raw.startswith("No news found"):
        return json.dumps({"ticker": ticker.upper(), "news": []}, indent=2)

    # Each headline is separated by a *blank* line in the returned blob
    items_raw = [s.strip() for s in raw.split("\n\n") if s.strip()][:10]

    news: List[Dict[str, str]] = []
    for blob in items_raw:
        title, *rest = blob.splitlines()
        body = " ".join(rest).strip()
        item = {"title": title.strip(), "body": body}

        if summarise:
            try:
                prompt = (
                    "Summarise the following market‑news item in ONE sentence:\n\n"
                    f"HEADLINE: {title}\nTEXT: {body}"
                )
                item["summary"] = _LLM.invoke(prompt, max_tokens=60).content.strip()
            except Exception as exc:
                LOGGER.warning("LLM summary failed: %s", exc)
                item["summary"] = ""

        news.append(item)

    return json.dumps({"ticker": ticker.upper(), "news": news}, indent=2)
