# Auto-generated MCP Server
# Source: {openapi_spec_file}
# Generated: {timestamp}

import asyncio
import json
import httpx
from typing import Any, Dict, List
from mcp.server import Server
from mcp.types import Tool, TextContent
from pydantic import AnyUrl

# Configuration
BASE_URL = "{base_url}"

# Initialize MCP server
server = Server("pizza-ordering-server")

{tool_definitions}

{tool_handlers}

async def main():
    # Run the server using stdin/stdout streams
    from mcp.server.stdio import stdio_server
    
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())
