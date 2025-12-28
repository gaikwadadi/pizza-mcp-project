"""
Abstract interface for external MCP clients with connection management.
"""
import asyncio
import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

class ExternalMCPError(Exception):
    """Base exception for external MCP client errors."""
    pass

class ConnectionError(ExternalMCPError):
    """Raised when connection to external MCP server fails."""
    pass

class ServiceUnavailableError(ExternalMCPError):
    """Raised when external service is temporarily unavailable."""
    pass

class ExternalMCPClient(ABC):
    """Abstract base class for external MCP service clients."""
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.logger = logging.getLogger(f"external_mcp.{service_name}")
        self.is_connected = False
        self.connection_retries = 0
        self.max_retries = 3
        
    @abstractmethod
    async def connect(self) -> bool:
        """Connect to the external MCP server."""
        pass
        
    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the external MCP server."""
        pass
        
    @abstractmethod
    async def list_tools(self) -> List[Dict[str, Any]]:
        """List available tools from the external MCP server."""
        pass
        
    @abstractmethod
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a specific tool on the external MCP server."""
        pass
        
    async def ensure_connected(self) -> bool:
        """Ensure connection is established with retry logic."""
        if self.is_connected:
            return True
            
        for attempt in range(self.max_retries):
            try:
                self.logger.info(f"Attempting to connect to {self.service_name} (attempt {attempt + 1})")
                success = await self.connect()
                if success:
                    self.is_connected = True
                    self.connection_retries = 0
                    self.logger.info(f"Successfully connected to {self.service_name}")
                    return True
            except Exception as e:
                self.logger.warning(f"Connection attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    
        self.logger.error(f"Failed to connect to {self.service_name} after {self.max_retries} attempts")
        raise ConnectionError(f"Unable to connect to {self.service_name}")
        
    async def safe_call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Safely call a tool with error handling and fallback."""
        try:
            await self.ensure_connected()
            result = await self.call_tool(tool_name, arguments)
            self.logger.info(f"Successfully called {tool_name} on {self.service_name}")
            return result
        except Exception as e:
            self.logger.error(f"Failed to call {tool_name} on {self.service_name}: {e}")
            raise ServiceUnavailableError(f"Service {self.service_name} unavailable: {e}")
