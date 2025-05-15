# app/mcp/manager.py

import logging
import asyncio
from typing import Dict, List, Optional
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_core.tools import StructuredTool, Tool
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
        self._loop = None  # Store a reference to the event loop

        logger.debug(f"Initialized MCPManager with {len(self._config)} servers")

    async def connect(self) -> None:
        """Initialize and connect to all configured MCP servers."""
        if self.client is not None:
            logger.info("MCP client already connected, skipping")
            return

        try:
            logger.info(f"Connecting to {len(self._config)} MCP servers...")
            # Get the current event loop or create a new one
            try:
                self._loop = asyncio.get_event_loop()
            except RuntimeError:
                self._loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._loop)

            # Create the client and enter the context
            client = MultiServerMCPClient(self._config)
            self.client = await client.__aenter__()

            # Get the tools after successful connection
            raw_tools = self.client.get_tools()

            # Convert tools to ensure they have both sync and async implementations
            self._tools = self.prepare_tools(raw_tools)

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
                raw_tools = self.client.get_tools()
                self._tools = self.prepare_tools(raw_tools)
            except Exception as e:
                logger.error(f"Error getting tools: {e}")
                return []

        return self._tools

    def prepare_tools(self, raw_tools: List[Tool]) -> List[Tool]:
        """
        Adapt MCP tools to work with LangGraph by ensuring the async tools are properly wrapped.
        """
        prepared_tools = []

        for tool in raw_tools:
            if isinstance(tool, StructuredTool):
                # Ensure the tool has a sync implementation that delegates to async
                if tool.coroutine and not tool.func:
                    # Create a sync wrapper that runs the async function in a loop
                    async_func = tool.coroutine

                    def create_sync_wrapper(async_fn):
                        def sync_wrapper(*args, **kwargs):
                            """Run async function in a new event loop."""
                            try:
                                # Use the manager's stored loop if available
                                if self._loop and not self._loop.is_closed():
                                    loop = self._loop
                                else:
                                    # Try to get the current event loop
                                    try:
                                        loop = asyncio.get_event_loop()
                                    except RuntimeError:
                                        # Create a new one if necessary
                                        loop = asyncio.new_event_loop()
                                        asyncio.set_event_loop(loop)
                                        # Store the new loop reference
                                        self._loop = loop

                                # Use the appropriate API based on whether the loop is running
                                if loop.is_running():
                                    logger.debug(
                                        f"Running async tool {tool.name} with run_coroutine_threadsafe"
                                    )
                                    future = asyncio.run_coroutine_threadsafe(
                                        async_fn(*args, **kwargs), loop
                                    )
                                    return future.result()
                                else:
                                    logger.debug(
                                        f"Running async tool {tool.name} with run_until_complete"
                                    )
                                    return loop.run_until_complete(
                                        async_fn(*args, **kwargs)
                                    )
                            except RuntimeError as e:
                                if "Event loop is closed" in str(e):
                                    logger.warning(
                                        f"Event loop was closed, creating a new one for tool {tool.name}"
                                    )
                                    # Create a new loop if the current one is closed
                                    new_loop = asyncio.new_event_loop()
                                    asyncio.set_event_loop(new_loop)
                                    self._loop = new_loop
                                    return new_loop.run_until_complete(
                                        async_fn(*args, **kwargs)
                                    )
                                else:
                                    logger.exception(
                                        f"Runtime error executing async tool {tool.name}: {e}"
                                    )
                                    raise
                            except Exception as e:
                                logger.exception(
                                    f"Error executing async tool {tool.name} in sync context: {e}"
                                )
                                raise RuntimeError(
                                    f"Failed to execute tool {tool.name}: {str(e)}"
                                )

                        return sync_wrapper

                    # Create and assign the wrapper
                    tool.func = create_sync_wrapper(async_func)

            prepared_tools.append(tool)

        return prepared_tools


# Global singleton instance
mcp_manager = MCPManager()


async def initialize_mcp_tools() -> List[Tool]:
    """Initialize MCP connections and return available tools."""
    await mcp_manager.connect()
    return mcp_manager.get_tools()


async def cleanup_mcp() -> None:
    """Clean up MCP connections."""
    await mcp_manager.disconnect()
