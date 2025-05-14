# app/mcp/servers.py

from app.config import COINMARKETCAP_API_KEY

MCP_SERVERS = {
    "coinmarketcap": {
        "transport": "stdio",
        "command": "npx",
        "args": ["-y", "@shinzolabs/coinmarketcap-mcp"],
        "env": {
            "COINMARKETCAP_API_KEY": COINMARKETCAP_API_KEY,
            "SUBSCRIPTION_LEVEL": "Basic",
        },
    },
}
