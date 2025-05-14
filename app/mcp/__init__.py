# app/mcp/__init__.py

import logging
from typing import List
from langchain_core.tools import Tool

logger = logging.getLogger(__name__)

# Start with an empty list - we'll initialize it properly when the app starts
MCP: List[Tool] = []

# Flag to track if MCP is initialized
MCP_INITIALIZED = False

__all__ = ["MCP", "cleanup_mcp", "initialize_app_mcp", "MCP_INITIALIZED"]


async def initialize_app_mcp():
    """Initialize MCP tools during application startup.

    This should be called as part of the application startup sequence,
    not during import time.
    """
    global MCP, MCP_INITIALIZED
    try:
        logger.info("→ initializing MCP servers…")
        # Only import here to avoid circular imports
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


async def cleanup_mcp():
    """Clean up MCP connections."""
    global MCP_INITIALIZED
    try:
        from app.mcp.manager import mcp_manager

        await mcp_manager.disconnect()
        MCP_INITIALIZED = False
    except Exception as e:
        logger.exception(f"Error during MCP cleanup: {e}")
