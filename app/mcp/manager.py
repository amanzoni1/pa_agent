# app/mcp/manager.py

import logging
import os
from typing import Dict, List, Optional
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_core.tools import Tool
from app.mcp.servers import MCP_SERVERS

logger = logging.getLogger(__name__)


class MCPManager:
    """Manager for Model Context Protocol servers."""

    _instance = None

    def __new__(cls, *args, **kwargs):
        """Ensure singleton pattern for the manager."""
        if cls._instance is None:
            cls._instance = super(MCPManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, config: Optional[Dict] = None):
        """Initialize the MCP Manager."""
        if getattr(self, "_initialized", False):
            return

        self._config = config or MCP_SERVERS
        self.client = None
        self._tools: List[Tool] = []
        self._initialized = True

        logger.debug(f"Initialized MCPManager with {len(self._config)} servers")

    async def connect(self) -> None:
        """Initialize and connect to all configured MCP servers."""
        if self.client is not None:
            logger.info("MCP client already connected, skipping")
            return

        try:
            logger.info(f"Connecting to {len(self._config)} MCP servers...")
            # Create the client and enter the context
            client = MultiServerMCPClient(self._config)
            self.client = await client.__aenter__()
            # Get the tools after successful connection
            self._tools = self.client.get_tools()
            logger.info(
                f"Connected successfully, loaded {len(self._tools)} tools: {[t.name for t in self._tools]}"
            )
        except Exception as e:
            logger.error(f"Failed to connect to MCP servers: {e}")
            if self.client:
                try:
                    await self.client.__aexit__(None, None, None)
                except Exception as cleanup_error:
                    logger.error(
                        f"Error during cleanup after failed connection: {cleanup_error}"
                    )
                self.client = None
                self._tools = []
            raise

    async def disconnect(self) -> None:
        """Gracefully disconnect from all MCP servers."""
        if not self.client:
            logger.info("No MCP client to disconnect")
            return

        logger.info("Disconnecting from MCP servers...")
        client = self.client
        self.client = None  # Clear reference first
        self._tools = []

        try:
            await client.__aexit__(None, None, None)
            logger.info("Successfully disconnected from MCP servers")
        except BaseExceptionGroup as bg:
            # This is expected for stdio clients sometimes
            logger.warning(f"Non-fatal errors during MCP disconnect: {bg}")
        except Exception as e:
            logger.error(f"Error during MCP disconnect: {e}")

    def get_tools(self) -> List[Tool]:
        """Retrieve all available tools from connected MCP servers."""
        if not self.client:
            logger.warning("No MCP client connected")
            return []

        if not self._tools:
            try:
                self._tools = self.client.get_tools()
            except Exception as e:
                logger.error(f"Error getting tools: {e}")
                return []

        return self._tools


# Global singleton instance
mcp_manager = MCPManager()


async def initialize_mcp_tools() -> List[Tool]:
    """Initialize MCP connections and return available tools."""
    await mcp_manager.connect()
    return mcp_manager.get_tools()


async def cleanup_mcp() -> None:
    """Clean up MCP connections."""
    await mcp_manager.disconnect()
