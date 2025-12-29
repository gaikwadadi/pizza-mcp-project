#!/usr/bin/env python3
"""
Complete HTTP-based MCP Server for Pizza API
Generated from complete OpenAPI specification
All 12 backend endpoints included
"""

import asyncio
import json
import logging
from typing import Any, Dict, List
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Base URL for the backend API
BASE_URL = "http://localhost:8000"

app = FastAPI(title="Pizza MCP Server (Complete)", version="2.0.0")

class MCPRequest(BaseModel):
    """MCP tool request model."""
    tool_name: str
    arguments: Dict[str, Any] = {}

class MCPResponse(BaseModel):
    """MCP tool response model."""
    success: bool
    data: Any = None
    error: str = None

class MCPTool(BaseModel):
    """MCP tool definition."""
    name: str
    description: str
    inputSchema: Dict[str, Any]

# Complete set of MCP tools (all 12 backend endpoints)
AVAILABLE_TOOLS = [
    MCPTool(
        name="get_health",
        description="Health Check",
        inputSchema={"type": "object", "properties": {}, "required": []}
    ),
    MCPTool(
        name="get_menu",
        description="Get Pizza Menu",
        inputSchema={"type": "object", "properties": {}, "required": []}
    ),
    MCPTool(
        name="get_orders",
        description="Get All Orders",
        inputSchema={"type": "object", "properties": {}, "required": []}
    ),
    MCPTool(
        name="create_orders",
        description="Create Pizza Order",
        inputSchema={
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "pizza": {"type": "string"},
                            "size": {"type": "string"},
                            "quantity": {"type": "integer", "default": 1},
                            "price": {"type": "number"}
                        },
                        "required": ["pizza", "size", "quantity", "price"]
                    }
                },
                "customer_email": {"type": "string"}
            },
            "required": ["items"]
        }
    ),
    MCPTool(
        name="get_orders_order_id",
        description="Get Order Status",
        inputSchema={
            "type": "object",
            "properties": {"order_id": {"type": "string"}},
            "required": ["order_id"]
        }
    ),
    MCPTool(
        name="update_orders_order_id",
        description="Update Order Status",
        inputSchema={
            "type": "object",
            "properties": {
                "order_id": {"type": "string"},
                "status": {"type": "string"}
            },
            "required": ["order_id", "status"]
        }
    ),
    MCPTool(
        name="create_admin_menu",
        description="Add Menu Item",
        inputSchema={
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "description": {"type": "string"},
                "price": {"type": "number"},
                "category": {"type": "string"}
            },
            "required": ["name", "price"]
        }
    ),
    MCPTool(
        name="create_orders_order_id_email",
        description="Update Order Email",
        inputSchema={
            "type": "object",
            "properties": {
                "order_id": {"type": "string"},
                "customer_email": {"type": "string"}
            },
            "required": ["order_id", "customer_email"]
        }
    ),
    MCPTool(
        name="create_orders_order_id_confirm",
        description="Confirm Order",
        inputSchema={
            "type": "object",
            "properties": {"order_id": {"type": "string"}},
            "required": ["order_id"]
        }
    ),
    MCPTool(
        name="create_orders_order_id_reject",
        description="Reject Order",
        inputSchema={
            "type": "object",
            "properties": {"order_id": {"type": "string"}},
            "required": ["order_id"]
        }
    ),
    MCPTool(
        name="create_orders_order_id_complete",
        description="Complete Order",
        inputSchema={
            "type": "object",
            "properties": {"order_id": {"type": "string"}},
            "required": ["order_id"]
        }
    ),
    MCPTool(
        name="get_stats_today",
        description="Get Today's Statistics",
        inputSchema={"type": "object", "properties": {}, "required": []}
    )
]

@app.get("/tools")
async def list_tools():
    """List all available MCP tools."""
    return [tool.dict() for tool in AVAILABLE_TOOLS]

@app.post("/call_tool")
async def call_tool(request: MCPRequest):
    """Call a specific MCP tool."""
    try:
        tool_name = request.tool_name
        arguments = request.arguments
        
        # Route to appropriate handler
        if tool_name == "get_health":
            result = await handle_get_health(arguments)
        elif tool_name == "get_menu":
            result = await handle_get_menu(arguments)
        elif tool_name == "get_orders":
            result = await handle_get_orders(arguments)
        elif tool_name == "create_orders":
            result = await handle_create_orders(arguments)
        elif tool_name == "get_orders_order_id":
            result = await handle_get_orders_order_id(arguments)
        elif tool_name == "update_orders_order_id":
            result = await handle_update_orders_order_id(arguments)
        elif tool_name == "create_admin_menu":
            result = await handle_create_admin_menu(arguments)
        elif tool_name == "create_orders_order_id_email":
            result = await handle_create_orders_order_id_email(arguments)
        elif tool_name == "create_orders_order_id_confirm":
            result = await handle_create_orders_order_id_confirm(arguments)
        elif tool_name == "create_orders_order_id_reject":
            result = await handle_create_orders_order_id_reject(arguments)
        elif tool_name == "create_orders_order_id_complete":
            result = await handle_create_orders_order_id_complete(arguments)
        elif tool_name == "get_stats_today":
            result = await handle_get_stats_today(arguments)
        else:
            raise HTTPException(status_code=400, detail=f"Unknown tool: {tool_name}")
        
        return MCPResponse(success=True, data=result)
        
    except Exception as e:
        logger.error(f"Error calling tool {request.tool_name}: {e}")
        return MCPResponse(success=False, error=str(e))

# Tool handlers for all 12 endpoints
async def handle_get_health(arguments: Dict[str, Any]):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/health")
        return response.json()

async def handle_get_menu(arguments: Dict[str, Any]):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/menu")
        return response.json()

async def handle_get_orders(arguments: Dict[str, Any]):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/orders")
        return response.json()

async def handle_create_orders(arguments: Dict[str, Any]):
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{BASE_URL}/orders", json=arguments)
        return response.json()

async def handle_get_orders_order_id(arguments: Dict[str, Any]):
    order_id = arguments["order_id"]
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/orders/{order_id}")
        return response.json()

async def handle_update_orders_order_id(arguments: Dict[str, Any]):
    order_id = arguments["order_id"]
    status_data = {"status": arguments["status"]}
    async with httpx.AsyncClient() as client:
        response = await client.put(f"{BASE_URL}/orders/{order_id}", json=status_data)
        return response.json()

async def handle_create_admin_menu(arguments: Dict[str, Any]):
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{BASE_URL}/admin/menu", json=arguments)
        return response.json()

async def handle_create_orders_order_id_email(arguments: Dict[str, Any]):
    order_id = arguments["order_id"]
    email_data = {"customer_email": arguments["customer_email"]}
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{BASE_URL}/orders/{order_id}/email", json=email_data)
        return response.json()

async def handle_create_orders_order_id_confirm(arguments: Dict[str, Any]):
    order_id = arguments["order_id"]
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{BASE_URL}/orders/{order_id}/confirm")
        return response.json()

async def handle_create_orders_order_id_reject(arguments: Dict[str, Any]):
    order_id = arguments["order_id"]
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{BASE_URL}/orders/{order_id}/reject")
        return response.json()

async def handle_create_orders_order_id_complete(arguments: Dict[str, Any]):
    order_id = arguments["order_id"]
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{BASE_URL}/orders/{order_id}/complete")
        return response.json()

async def handle_get_stats_today(arguments: Dict[str, Any]):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/stats/today")
        return response.json()

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "Pizza MCP Server (Complete)", "tools": len(AVAILABLE_TOOLS)}

if __name__ == "__main__":
    import uvicorn
    logger.info("🚀 Starting Complete Pizza MCP Server (HTTP)")
    logger.info("📡 MCP Tools: http://localhost:3000/tools")
    logger.info("🔧 Call Tool: http://localhost:3000/call_tool")
    logger.info("❤️  Health: http://localhost:3000/health")
    logger.info(f"🛠️  Total Tools: {len(AVAILABLE_TOOLS)}")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=3000,
        reload=False,
    )
