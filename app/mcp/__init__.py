# app/mcp/__init__.py

import asyncio
import logging
from typing import List
from langchain_core.tools import Tool

logger = logging.getLogger(__name__)

# Start with an empty list
MCP: List[Tool] = []
MCP_INITIALIZED = False
# Store a reference to the event loop for reuse
MCP_LOOP = None


# Initialize MCP synchronously at import time
def _initialize_mcp():
    global MCP, MCP_INITIALIZED, MCP_LOOP
    if not MCP_INITIALIZED:
        try:
            logger.info("→ initializing MCP servers at import time…")
            # Create a new event loop, but don't close it
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            MCP_LOOP = loop  # Store the loop for reuse

            from app.mcp.manager import initialize_mcp_tools

            MCP = loop.run_until_complete(initialize_mcp_tools())

            # Don't close the loop here
            MCP_INITIALIZED = True
            logger.info(f"→ loaded {len(MCP)} MCP tools: {[t.name for t in MCP]}")
        except Exception as e:
            logger.exception(f"→ MCP init failed at import time: {e}")
            MCP = []
            MCP_INITIALIZED = False


# Initialize at import time
_initialize_mcp()


# Keep these functions for explicit initialization/cleanup when needed
async def initialize_app_mcp():
    """Initialize MCP tools during application startup if not already done."""
    global MCP, MCP_INITIALIZED
    if not MCP_INITIALIZED:
        try:
            logger.info("→ initializing MCP servers…")
            from app.mcp.manager import initialize_mcp_tools

            MCP = await initialize_mcp_tools()
            MCP_INITIALIZED = True
            logger.info(f"→ loaded {len(MCP)} MCP tools: {[t.name for t in MCP]}")
            return MCP
        except Exception as e:
            logger.exception(f"→ MCP init failed: {e}")
            MCP = []
            MCP_INITIALIZED = False
            return MCP
    return MCP


async def cleanup_mcp():
    """Clean up MCP connections."""
    global MCP_INITIALIZED, MCP_LOOP
    try:
        from app.mcp.manager import mcp_manager

        await mcp_manager.disconnect()
        MCP_INITIALIZED = False

        # Don't close the loop here either, as it might be needed later
    except Exception as e:
        logger.exception(f"Error during MCP cleanup: {e}")


__all__ = ["MCP", "cleanup_mcp", "initialize_app_mcp", "MCP_INITIALIZED"]
