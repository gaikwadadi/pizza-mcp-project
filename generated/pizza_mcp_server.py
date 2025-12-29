# Auto-generated MCP Server
# Source: specs/pizza_openapi.json
# Generated: 2025-12-27T22:18:52.640864

import asyncio
import json
import httpx
from typing import Any, Dict, List
from mcp.server import Server
from mcp.types import Tool, TextContent
from pydantic import AnyUrl

# Configuration
BASE_URL = "http://localhost:8000"

# Initialize MCP server
server = Server("pizza-ordering-server")

@server.list_tools()
async def handle_list_tools() -> List[Tool]:
    return [
        Tool(
            name="get_health",
            description="Health Check",
            inputSchema=        {
                    "type": "object",
                    "properties": {},
                    "required": []
        }
        ),
        Tool(
            name="get_menu",
            description="Get Pizza Menu",
            inputSchema=        {
                    "type": "object",
                    "properties": {},
                    "required": []
        }
        ),
        Tool(
            name="get_orders",
            description="Get All Orders",
            inputSchema=        {
                    "type": "object",
                    "properties": {},
                    "required": []
        }
        ),
        Tool(
            name="create_orders",
            description="Create Pizza Order",
            inputSchema=        {
                    "type": "object",
                    "properties": {
                                "items": {
                                            "type": "array",
                                            "items": {
                                                        "type": "object",
                                                        "properties": {},
                                                        "required": []
                                            }
                                },
                                "customer_email": {
                                            "type": "object",
                                            "properties": {},
                                            "required": []
                                }
                    },
                    "required": [
                                "items"
                    ]
        }
        ),
        Tool(
            name="get_orders_order_id",
            description="Get Order Status",
            inputSchema=        {
                    "type": "object",
                    "properties": {
                                "order_id": {
                                            "type": "string",
                                            "title": "Order Id"
                                }
                    },
                    "required": [
                                "order_id"
                    ]
        }
        ),
        Tool(
            name="update_orders_order_id",
            description="Update Order Status",
            inputSchema=        {
                    "type": "object",
                    "properties": {
                                "order_id": {
                                            "type": "string",
                                            "title": "Order Id"
                                }
                    },
                    "required": [
                                "order_id"
                    ]
        }
        ),
        Tool(
            name="create_admin_menu",
            description="Add Menu Item Endpoint",
            inputSchema=        {
                    "type": "object",
                    "properties": {
                                "name": {
                                            "type": "string",
                                            "title": "Name"
                                },
                                "price": {
                                            "type": "number",
                                            "title": "Price"
                                },
                                "sizes": {
                                            "type": "array",
                                            "items": {
                                                        "type": "string"
                                            }
                                },
                                "description": {
                                            "type": "object",
                                            "properties": {},
                                            "required": []
                                }
                    },
                    "required": [
                                "name",
                                "price",
                                "sizes"
                    ]
        }
        ),
        Tool(
            name="create_orders_order_id_email",
            description="Update Order Email",
            inputSchema=        {
                    "type": "object",
                    "properties": {
                                "order_id": {
                                            "type": "string",
                                            "title": "Order Id"
                                }
                    },
                    "required": [
                                "order_id"
                    ]
        }
        ),
        Tool(
            name="create_orders_order_id_confirm",
            description="Confirm Order",
            inputSchema=        {
                    "type": "object",
                    "properties": {
                                "order_id": {
                                            "type": "string",
                                            "title": "Order Id"
                                }
                    },
                    "required": [
                                "order_id"
                    ]
        }
        ),
        Tool(
            name="create_orders_order_id_reject",
            description="Reject Order",
            inputSchema=        {
                    "type": "object",
                    "properties": {
                                "order_id": {
                                            "type": "string",
                                            "title": "Order Id"
                                }
                    },
                    "required": [
                                "order_id"
                    ]
        }
        ),
        Tool(
            name="create_orders_order_id_complete",
            description="Complete Order",
            inputSchema=        {
                    "type": "object",
                    "properties": {
                                "order_id": {
                                            "type": "string",
                                            "title": "Order Id"
                                }
                    },
                    "required": [
                                "order_id"
                    ]
        }
        ),
        Tool(
            name="get_stats_today",
            description="Get Today Stats",
            inputSchema=        {
                    "type": "object",
                    "properties": {},
                    "required": []
        }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    if name == "get_health":
        return await get_health_handler(arguments)
    if name == "get_menu":
        return await get_menu_handler(arguments)
    if name == "get_orders":
        return await get_orders_handler(arguments)
    if name == "create_orders":
        return await create_orders_handler(arguments)
    if name == "get_orders_order_id":
        return await get_orders_order_id_handler(arguments)
    if name == "update_orders_order_id":
        return await update_orders_order_id_handler(arguments)
    if name == "create_admin_menu":
        return await create_admin_menu_handler(arguments)
    if name == "create_orders_order_id_email":
        return await create_orders_order_id_email_handler(arguments)
    if name == "create_orders_order_id_confirm":
        return await create_orders_order_id_confirm_handler(arguments)
    if name == "create_orders_order_id_reject":
        return await create_orders_order_id_reject_handler(arguments)
    if name == "create_orders_order_id_complete":
        return await create_orders_order_id_complete_handler(arguments)
    if name == "get_stats_today":
        return await get_stats_today_handler(arguments)
    
    raise ValueError(f"Unknown tool: {name}")

async def get_health_handler(arguments: Dict[str, Any]) -> List[TextContent]:
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/health")
        return [TextContent(type="text", text=json.dumps(response.json()))]

async def get_menu_handler(arguments: Dict[str, Any]) -> List[TextContent]:
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/menu")
        return [TextContent(type="text", text=json.dumps(response.json()))]

async def get_orders_handler(arguments: Dict[str, Any]) -> List[TextContent]:
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/orders")
        return [TextContent(type="text", text=json.dumps(response.json()))]

async def create_orders_handler(arguments: Dict[str, Any]) -> List[TextContent]:
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{BASE_URL}/orders", json=arguments)
        return [TextContent(type="text", text=json.dumps(response.json()))]

async def get_orders_order_id_handler(arguments: Dict[str, Any]) -> List[TextContent]:
    async with httpx.AsyncClient() as client:
        url = f"{BASE_URL}/orders/{arguments['order_id']}"
        response = await client.get(url)
        return [TextContent(type="text", text=json.dumps(response.json()))]

async def update_orders_order_id_handler(arguments: Dict[str, Any]) -> List[TextContent]:
    async with httpx.AsyncClient() as client:
        response = await client.put(f"{BASE_URL}/orders/{order_id}", json=arguments)
        return [TextContent(type="text", text=json.dumps(response.json()))]

async def create_admin_menu_handler(arguments: Dict[str, Any]) -> List[TextContent]:
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{BASE_URL}/admin/menu", json=arguments)
        return [TextContent(type="text", text=json.dumps(response.json()))]

async def create_orders_order_id_email_handler(arguments: Dict[str, Any]) -> List[TextContent]:
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{BASE_URL}/orders/{order_id}/email", json=arguments)
        return [TextContent(type="text", text=json.dumps(response.json()))]

async def create_orders_order_id_confirm_handler(arguments: Dict[str, Any]) -> List[TextContent]:
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{BASE_URL}/orders/{order_id}/confirm", json=arguments)
        return [TextContent(type="text", text=json.dumps(response.json()))]

async def create_orders_order_id_reject_handler(arguments: Dict[str, Any]) -> List[TextContent]:
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{BASE_URL}/orders/{order_id}/reject", json=arguments)
        return [TextContent(type="text", text=json.dumps(response.json()))]

async def create_orders_order_id_complete_handler(arguments: Dict[str, Any]) -> List[TextContent]:
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{BASE_URL}/orders/{order_id}/complete", json=arguments)
        return [TextContent(type="text", text=json.dumps(response.json()))]

async def get_stats_today_handler(arguments: Dict[str, Any]) -> List[TextContent]:
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/stats/today")
        return [TextContent(type="text", text=json.dumps(response.json()))]

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
