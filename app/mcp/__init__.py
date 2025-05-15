# app/mcp/__init__.py

import asyncio
import logging
from typing import List
from langchain_core.tools import Tool

logger = logging.getLogger(__name__)

# Start with an empty list
MCP: List[Tool] = []
MCP_INITIALIZED = False


# Initialize MCP tools at import time
def _initialize_mcp():
    global MCP, MCP_INITIALIZED
    if not MCP_INITIALIZED:
        try:
            logger.info("→ initializing MCP servers at import time…")
            # Create a new event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            from app.mcp.manager import initialize_mcp_tools

            MCP = loop.run_until_complete(initialize_mcp_tools())

            MCP_INITIALIZED = True
            logger.info(f"→ loaded {len(MCP)} MCP tools: {[t.name for t in MCP]}")
        except Exception as e:
            logger.exception(f"→ MCP init failed at import time: {e}")
            MCP = []
            MCP_INITIALIZED = False


# Initialize at import time
_initialize_mcp()


async def cleanup_mcp():
    """Clean up MCP connections."""
    global MCP_INITIALIZED
    try:
        from app.mcp.manager import mcp_manager

        await mcp_manager.disconnect()
        MCP_INITIALIZED = False

    except Exception as e:
        logger.exception(f"Error during MCP cleanup: {e}")


__all__ = ["MCP", "cleanup_mcp"]
