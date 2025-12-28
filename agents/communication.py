"""
Agent-to-Agent communication protocol for structured message passing.
"""
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from enum import Enum
from pydantic import BaseModel, Field
from utils.timezone_utils import tz_manager

class A2AMessageType(Enum):
    """Types of messages exchanged between agents."""
    ORDER_PLACED = "order_placed"
    SCHEDULE_REQUEST = "schedule_request"
    SCHEDULE_CONFIRMED = "schedule_confirmed"
    SCHEDULE_FAILED = "schedule_failed"
    STATUS_UPDATE = "status_update"
    ERROR_NOTIFICATION = "error_notification"

class A2AMessage(BaseModel):
    """Structured message for agent-to-agent communication."""
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: A2AMessageType
    from_agent: str
    to_agent: str
    payload: Dict[str, Any]
    correlation_id: str
    timestamp: str = Field(default_factory=lambda: tz_manager.format_for_storage(tz_manager.now_utc()))
    retry_count: int = 0
    
    class Config:
        use_enum_values = True

class OrderPlacedMessage(BaseModel):
    """Payload for ORDER_PLACED message."""
    order_id: str
    prep_time: str
    estimated_ready: str
    customer_info: Dict[str, Any]
    items: list[Dict[str, Any]]
    total_price: float

class ScheduleConfirmedMessage(BaseModel):
    """Payload for SCHEDULE_CONFIRMED message."""
    order_id: str
    delivery_time: str
    delivery_window: Dict[str, str]  # start_time, end_time
    delivery_instructions: Optional[str] = None

class ScheduleFailedMessage(BaseModel):
    """Payload for SCHEDULE_FAILED message."""
    order_id: str
    reason: str
    suggested_alternatives: list[str] = []
    retry_possible: bool = True

class A2AMessageBus:
    """Simple message bus for agent communication using LangGraph state."""
    
    async def send_message(self, message: A2AMessage):
        """Send A2A message to target agent."""
        try:
            # For now, we'll use a simple HTTP notification to the chat server
            # which will forward the message to the appropriate agent
            import httpx
            async with httpx.AsyncClient() as client:
                # Send to chat server's A2A endpoint
                response = await client.post(
                    "http://localhost:8001/api/a2a-message",
                    json=message.dict(),
                    timeout=5.0
                )
                if response.status_code == 200:
                    print(f"A2A message sent successfully: {message.type}")
                else:
                    print(f"Failed to send A2A message: {response.status_code}")
        except Exception as e:
            print(f"Error sending A2A message: {e}")
    
    @staticmethod
    def create_order_placed_message(
        from_agent: str,
        to_agent: str,
        order_data: Dict[str, Any],
        correlation_id: str
    ) -> A2AMessage:
        """Create ORDER_PLACED message."""
        payload = OrderPlacedMessage(**order_data).dict()
        
        return A2AMessage(
            type=A2AMessageType.ORDER_PLACED,
            from_agent=from_agent,
            to_agent=to_agent,
            payload=payload,
            correlation_id=correlation_id
        )
    
    @staticmethod
    def create_schedule_confirmed_message(
        from_agent: str,
        to_agent: str,
        schedule_data: Dict[str, Any],
        correlation_id: str
    ) -> A2AMessage:
        """Create SCHEDULE_CONFIRMED message."""
        payload = ScheduleConfirmedMessage(**schedule_data).dict()
        
        return A2AMessage(
            type=A2AMessageType.SCHEDULE_CONFIRMED,
            from_agent=from_agent,
            to_agent=to_agent,
            payload=payload,
            correlation_id=correlation_id
        )
    
    @staticmethod
    def create_schedule_failed_message(
        from_agent: str,
        to_agent: str,
        failure_data: Dict[str, Any],
        correlation_id: str
    ) -> A2AMessage:
        """Create SCHEDULE_FAILED message."""
        payload = ScheduleFailedMessage(**failure_data).dict()
        
        return A2AMessage(
            type=A2AMessageType.SCHEDULE_FAILED,
            from_agent=from_agent,
            to_agent=to_agent,
            payload=payload,
            correlation_id=correlation_id
        )
