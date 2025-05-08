# app/tools/finance_tools.py

import logging
import json
import re
from typing import List, Dict, Any, Sequence

import yfinance as yf
from langchain_core.tools import tool
from langchain_community.tools.yahoo_finance_news import YahooFinanceNewsTool
from app.config import get_llm


logger = logging.getLogger(__name__)

_LLM = get_llm()
yf_news_tool = YahooFinanceNewsTool()


# helpers
def _normalise_tickers(raw: str | Sequence[str]) -> List[str]:
    """
    Accepts "MSFT, NVDA" | "MSFT NVDA" | ["MSFT","NVDA"] → ["MSFT","NVDA"].
    """
    if isinstance(raw, str):
        tickers = re.split(r"[,\s]+", raw.strip())
    else:
        tickers = list(raw)
    return [t.upper() for t in tickers if t]


# LangGraph tools
@tool
def get_stock_quote(tickers: str | Sequence[str]) -> List[Dict[str, Any]]:
    """
    Fetch the latest quote and basic market data for one or more tickers.

    Args:
      tickers: comma- or space-separated string, or list of symbols.

    Returns:
      A list of dicts, each with keys:
        - ticker (str)
        - price (float)
        - currency (str)
        - previous_close (float)
        - open (float)
        - day_range (str)
    """
    results: List[Dict[str, Any]] = []
    for t in _normalise_tickers(tickers):
        try:
            tk = yf.Ticker(t)
            info = tk.info
            results.append(
                {
                    "ticker": t,
                    "price": info.get("regularMarketPrice"),
                    "currency": info.get("currency"),
                    "previous_close": info.get("regularMarketPreviousClose"),
                    "open": info.get("regularMarketOpen"),
                    "day_range": f"{info.get('regularMarketDayLow')} - {info.get('regularMarketDayHigh')}",
                }
            )
        except Exception:
            logger.exception("get_stock_quote failed for ticker=%r", t)
            results.append(
                {
                    "ticker": t,
                    "price": None,
                    "currency": None,
                    "previous_close": None,
                    "open": None,
                    "day_range": "",
                }
            )
    return results


@tool
def get_stock_news(
    tickers: str | Sequence[str],
    summarise: bool = True,
    max_items: int = 10,
) -> str:
    """
    ➜ Latest Yahoo‑Finance headlines for tickers (max `max_items`).

    Args:
      tickers: comma‑ or space‑separated string, or list of stock symbols.
      summarise:  If True, add a 1‑sentence LLM summary per item.
      max_items: Number of headlines per ticker (up to 10).

    Returns:
      JSON string of either a single dict
        {"ticker": str, "news": [ {title, body, summary?}, … ] }
      or a list of such dicts for multiple tickers.
    """
    output: List[Dict[str, Any]] = []
    for t in _normalise_tickers(tickers):
        raw = yf_news_tool.invoke(t) or ""
        if raw.startswith("No news found"):
            output.append({"ticker": t, "news": []})
            continue
        items = [b.strip() for b in raw.split("\n\n") if b.strip()][:max_items]
        news_items: List[Dict[str, str]] = []
        for blob in items:
            lines = blob.splitlines()
            title = lines[0].strip()
            body = " ".join(lines[1:]).strip()
            item: Dict[str, str] = {"title": title, "body": body}
            if summarise:
                try:
                    prompt = (
                        f"Summarise the following market‑news item in ONE sentence:\n\n"
                        f"HEADLINE: {title}\nTEXT: {body}"
                    )
                    summary = _LLM.invoke(prompt, max_tokens=60).content.strip()
                    item["summary"] = summary
                except Exception as exc:
                    logger.warning("LLM summary failed for %s: %s", t, exc)
            news_items.append(item)
        output.append({"ticker": t, "news": news_items})
    # Return a JSON string
    result = output[0] if isinstance(tickers, str) or len(output) == 1 else output
    return json.dumps(result, indent=2)
