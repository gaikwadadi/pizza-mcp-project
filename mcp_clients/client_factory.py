"""
Factory for creating external MCP clients with configuration management.
"""
import os
from typing import Dict, Any, Optional
from enum import Enum

from .external_client import ExternalMCPClient

class ExternalServiceType(Enum):
    """Supported external MCP service types."""
    # Future services can be added here
    # SLACK = "slack"
    # TWILIO = "twilio"
    pass

class ExternalMCPClientFactory:
    """Factory for creating external MCP clients."""
    
    _clients: Dict[str, ExternalMCPClient] = {}
    
    @classmethod
    def create_client(
        cls, 
        service_type: ExternalServiceType, 
        config: Optional[Dict[str, Any]] = None
    ) -> ExternalMCPClient:
        """Create or return existing external MCP client."""
        
        service_key = service_type.value
        
        # Return existing client if already created
        if service_key in cls._clients:
            return cls._clients[service_key]
            
        # No supported services currently
        raise ValueError(f"Unsupported service type: {service_type}")
        
    @classmethod
    def get_client(cls, service_type: ExternalServiceType) -> Optional[ExternalMCPClient]:
        """Get existing client without creating new one."""
        return cls._clients.get(service_type.value)
        
    @classmethod
    async def disconnect_all(cls) -> None:
        """Disconnect all external MCP clients."""
        for client in cls._clients.values():
            if client.is_connected:
                await client.disconnect()
        cls._clients.clear()
        
    @classmethod
    def get_available_services(cls) -> list[str]:
        """Get list of available external service types."""
        return [service.value for service in ExternalServiceType]
