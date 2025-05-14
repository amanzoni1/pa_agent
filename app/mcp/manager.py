# app/mcp/manager.py

import asyncio
from typing import List
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_core.tools import Tool
from app.mcp.servers import MCP_SERVERS


class MCPManager:
    def __init__(self, config=None):
        self._config = config or MCP_SERVERS
        self.client = None
        self._tools = []

    async def connect(self):
        """Initialize the MultiServerMCPClient and connect to all servers."""
        if self.client is None:
            self.client = await MultiServerMCPClient(self._config).__aenter__()
            self._tools = self.client.get_tools()

    async def disconnect(self):
        """Gracefully tear down connections."""
        if self.client:
            await self.client.__aexit__(None, None, None)
            self.client = None
            self._tools = []

    def get_tools(self) -> List[Tool]:
        """Return the loaded MCP tools as LangChain-style Tool objects."""
        if self.client:
            return self.client.get_tools()
        return []


# Create a singleton instance
mcp_manager = MCPManager()


# Function to initialize and get tools
async def initialize_mcp_tools() -> List[Tool]:
    await mcp_manager.connect()
    return mcp_manager.get_tools()


# Function to clean up
async def cleanup_mcp():
    await mcp_manager.disconnect()
