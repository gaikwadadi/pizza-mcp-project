"""
HTTP-based MCP client for communicating with the pizza MCP server.
"""
import json
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

@dataclass
class MCPResponse:
    """Structured MCP response."""
    success: bool
    data: Any = None
    error: Optional[str] = None
    tool_name: Optional[str] = None

class PizzaMCPClient:
    """Pure HTTP-based client for communicating with the pizza MCP server."""
    
    def __init__(self, mcp_base_url: str = "http://localhost:3000"):
        """Initialize HTTP MCP client."""
        self.mcp_base_url = mcp_base_url
        self.logger = logging.getLogger("mcp_client.pizza")
        self.available_tools = []
        self.connected = False
        
    def is_connected(self) -> bool:
        """Check if client is connected to MCP server."""
        return self.connected
        
    async def connect(self) -> bool:
        """Connect to the HTTP-based MCP server."""
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.mcp_base_url}/tools", timeout=5.0)
                if response.status_code == 200:
                    tools = response.json()
                    self.available_tools = tools
                    self.connected = True
                    self.logger.info(f"Connected to HTTP MCP server: {len(tools)} tools available")
                    return True
                else:
                    self.connected = False
                    self.logger.error(f"MCP server connection failed: {response.status_code}")
                    return False
            
        except Exception as e:
            self.connected = False
            self.logger.error(f"Failed to connect to HTTP MCP server: {e}")
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from MCP server."""
        self.connected = False
        self.available_tools = []
        self.logger.info("Disconnected from HTTP MCP server")
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any] = None) -> MCPResponse:
        """Call a specific MCP tool via HTTP."""
        try:
            import httpx
            request_data = {
                "tool_name": tool_name,
                "arguments": arguments or {}
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.mcp_base_url}/call_tool", 
                    json=request_data, 
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    mcp_response = response.json()
                    if mcp_response.get("success"):
                        return MCPResponse(
                            success=True, 
                            data=mcp_response.get("data"),
                            tool_name=tool_name
                        )
                    else:
                        return MCPResponse(
                            success=False, 
                            error=mcp_response.get("error"),
                            tool_name=tool_name
                        )
                else:
                    return MCPResponse(
                        success=False, 
                        error=f"HTTP error: {response.status_code}",
                        tool_name=tool_name
                    )
                    
        except Exception as e:
            self.logger.error(f"Failed to call tool {tool_name}: {e}")
            return MCPResponse(
                success=False, 
                error=str(e),
                tool_name=tool_name
            )
    
    async def get_menu(self) -> MCPResponse:
        """Get pizza menu via HTTP MCP server."""
        return await self.call_tool("get_menu")
    
    async def create_order(self, items: list, customer_email: str = None) -> MCPResponse:
        """Create pizza order via HTTP MCP server."""
        return await self.call_tool("create_orders", {
            "items": items,
            "customer_email": customer_email
        })
