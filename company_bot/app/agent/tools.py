import os
from typing import Literal
from tavily import TavilyClient
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())


# Initialize Client
api_key = os.getenv("TAVILY_API_KEY")
tavily_client = TavilyClient(api_key=api_key)

def internet_search(
    query: str,
    max_results: int = 5,
    topic: Literal["general", "news", "finance"] = "general",
):
    """
    Run a web search using Tavily.
    Use this to find up-to-date information about companies or general knowledge.
    """
    return tavily_client.search(
        query,
        max_results=max_results,
        topic=topic,
    )
