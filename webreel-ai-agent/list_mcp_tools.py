import asyncio
import os
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def list_tools():
    mcp_path = r"f:\==HK1-2526==\ThucTap\webreel\playwright-mcp\packages\playwright-mcp\cli.js"
    server_params = StdioServerParameters(
        command="node",
        args=[mcp_path, "--cdp-endpoint=http://localhost:9222"],
        env=os.environ.copy()
    )
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            for tool in tools.tools:
                print(f"TOOL: {tool.name}")
                print(f"  Description: {tool.description}")
                print(f"  Input Schema: {tool.inputSchema}")
                print("-" * 20)

if __name__ == "__main__":
    asyncio.run(list_tools())
