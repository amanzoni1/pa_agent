# app/mcp/servers.py

MCP_SERVERS = {
    "math": {
        "transport": "stdio",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-math"],
    },
    "python": {
        "transport": "stdio",
        "command": "python",
        "args": ["-m", "mcp_python_server"],
    },
    "currency": {
        "transport": "stdio",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-currency"],
    },
    "image": {
        "transport": "stdio",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-image-gen"],
    },
}
