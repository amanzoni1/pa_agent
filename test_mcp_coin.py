# test_mcp_coin.py
import os
import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient
from dotenv import load_dotenv

load_dotenv()

# 1) Point at your CMC MCP server; adjust the package name if needed:
MCP_CONFIG = {
    "coinmarketcap": {
        "transport": "stdio",
        "command": "npx",
        "args": ["-y", "@shinzolabs/coinmarketcap-mcp"],
        "env": {
            # must set your key in the shell first:
            "COINMARKETCAP_API_KEY": "74e465e7-df66-487a-9e2a-7ca144bd3b22",
            "SUBSCRIPTION_LEVEL": "Basic",
            # avoid the USER_AGENT warning:
            # "USER_AGENT": os.environ.get("USER_AGENT", "my-mcp-client/0.1"),
        },
    }
}


async def main():
    async with MultiServerMCPClient(MCP_CONFIG) as client:
        tools = client.get_tools()
        names = [t.name for t in tools]
        print("Available MCP tools:", names, "\n")

        # 1) cryptoCategories
        cats_tool = next(t for t in tools if t.name == "cryptoCategories")
        cats = await cats_tool.arun({"start": 1, "limit": 5})
        print("cryptoCategories →", cats, "\n")

        # 2) globalMetricsLatest
        global_tool = next(t for t in tools if t.name == "globalMetricsLatest")
        metrics = await global_tool.arun({"convert": "EUR"})
        print("globalMetricsLatest →", metrics, "\n")


if __name__ == "__main__":
    # make sure your .env has COINMARKETCAP_API_KEY
    asyncio.run(main())
