"""
Pizza scheduling agent for coordinating delivery times with external calendar services.
"""
import asyncio
import os
from typing import Dict, Any, Optional, TypedDict
from datetime import datetime, timedelta

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledStateGraph

from .agent_base import AgentBase
from .communication import A2AMessage, A2AMessageType, A2AMessageBus
from utils.timezone_utils import tz_manager
from services.free_email_service import FreeEmailService

# Initialize email service
free_email_service = FreeEmailService()

class SchedulingState(TypedDict):
    """LangGraph state for scheduling workflow."""
    # Input
    incoming_message: Optional[A2AMessage]
    order_data: Optional[Dict[str, Any]]
    
    # Processing
    delivery_window: Optional[Dict[str, str]]
    selected_time_slot: Optional[str]
    
    # Output
    schedule_result: Optional[Dict[str, Any]]
    outgoing_message: Optional[A2AMessage]
    
    # Control
    current_node: str
    retry_count: int
    error_context: Optional[Dict[str, Any]]

class PizzaSchedulingAgent(AgentBase):
    """AI agent for scheduling pizza deliveries with external calendar integration."""
    
    def __init__(self):
        """Initialize the scheduling agent."""
        # Get temperature with validation
        temp_str = os.getenv("SCHEDULING_AGENT_TEMPERATURE")
        temperature = None
        if temp_str:
            try:
                temperature = float(temp_str)
            except ValueError:
                raise ValueError(f"SCHEDULING_AGENT_TEMPERATURE must be a valid number, got: {temp_str}")
        
        super().__init__(
            agent_id="scheduling_agent",
            agent_name=os.getenv("SCHEDULING_AGENT_NAME"),
            model_name=os.getenv("GROQ_MODEL_ID"),
            temperature=temperature
        )
        
        # Configuration
        self.delivery_window_minutes = int(os.getenv("DEFAULT_DELIVERY_WINDOW_MINUTES", "30"))
        self.prep_buffer_minutes = int(os.getenv("DEFAULT_PREP_BUFFER_MINUTES", "5"))
        
        # External services
        self.calendar_client = None
        self.message_bus = A2AMessageBus()
        
        # Build workflow
        self.workflow = self._build_workflow()
        
    def _build_workflow(self) -> CompiledStateGraph:
        """Build the scheduling workflow using LangGraph."""
        workflow = StateGraph(SchedulingState)
        
        # Add nodes
        workflow.add_node("receive_order", self._receive_order)
        workflow.add_node("process_business_message", self._process_business_message)
        workflow.add_node("calculate_delivery_window", self._calculate_delivery_window)
        workflow.add_node("schedule_delivery", self._schedule_delivery)
        workflow.add_node("send_confirmation", self._send_confirmation)
        workflow.add_node("handle_scheduling_error", self._handle_scheduling_error)
        
        # Add edges
        workflow.set_entry_point("receive_order")
        workflow.add_edge("receive_order", "process_business_message")
        workflow.add_edge("process_business_message", "calculate_delivery_window")
        workflow.add_edge("calculate_delivery_window", "schedule_delivery")
        
        workflow.add_edge("schedule_delivery", "send_confirmation")
        workflow.add_edge("send_confirmation", END)
        workflow.add_edge("handle_scheduling_error", END)
        
        return workflow.compile()
        
    async def process_order_message(self, message: A2AMessage) -> A2AMessage:
        """Process incoming order message and return scheduling result."""
        try:
            # Initialize external services
            await self._ensure_external_services()
            
            # Create initial state
            initial_state = {
                "incoming_message": message,
                "order_data": message.payload,
                "delivery_window": None,
                "selected_time_slot": None,
                "schedule_result": None,
                "outgoing_message": None,
                "current_node": "receive_order",
                "retry_count": 0,
                "error_context": None
            }
            
            # Run workflow
            result = await self.workflow.ainvoke(initial_state)
            
            self.logger.info(f"Scheduling completed for order {message.payload.get('order_id')}")
            return result.get("outgoing_message")
            
        except Exception as e:
            self.logger.error(f"Scheduling workflow failed: {e}")
            return self._create_error_message(message, str(e))
            
    async def _ensure_external_services(self):
        """Ensure external services are connected."""
        if not self.calendar_client:
            # Use email service instead of calendar for A2A demonstration
            print("📧 Using email notifications instead of calendar")
            
            
    async def _receive_order(self, state: SchedulingState) -> SchedulingState:
        """Receive and validate incoming order message."""
        message = state["incoming_message"]
        
        if not message or message.type != A2AMessageType.ORDER_PLACED.value:
            state["error_context"] = {
                "node": "receive_order",
                "error": "Invalid or missing order message"
            }
            return state
        
        # Check if payload exists and is accessible
        if not hasattr(message, 'payload') or message.payload is None:
            state["error_context"] = {
                "node": "receive_order",
                "error": "Message payload is missing or None"
            }
            return state
            
        order_data = message.payload
        
        # Ensure order_data is a dictionary
        if not isinstance(order_data, dict):
            state["error_context"] = {
                "node": "receive_order",
                "error": f"Invalid payload type: {type(order_data)}"
            }
            return state
            
        required_fields = ["order_id", "estimated_ready"]
        
        for field in required_fields:
            if field not in order_data:
                state["error_context"] = {
                    "node": "receive_order",
                    "error": f"Missing required field: {field}"
                }
                return state
                
        self.logger.info(f"Received order for scheduling: {order_data.get('order_id')}")
        state["order_data"] = order_data  # Store order_data in state
        state["current_node"] = "process_business_message"
        return state
    
    async def _process_business_message(self, state: SchedulingState) -> SchedulingState:
        """Process A2A messages from business dashboard for email notifications."""
        try:
            message = state.get("incoming_message")
            if message and message.payload:
                action = message.payload.get("action")
                
                if action == "order_confirmed":
                    # Send order confirmation email with delivery time
                    await self._send_order_confirmed_email(message.payload)
                    state["current_node"] = "calculate_delivery_window"
                    
                elif action == "order_ready":
                    # Send order ready email
                    await self._send_order_ready_email(message.payload)
                    state["current_node"] = END
                    state["current_node"] = END
                    
                else:
                    # Regular scheduling flow
                    state["current_node"] = "calculate_delivery_window"
            else:
                state["current_node"] = "calculate_delivery_window"
                
        except Exception as e:
            self.logger.error(f"Error processing business message: {e}")
            state["current_node"] = "calculate_delivery_window"
            
        return state
        
    async def _calculate_delivery_window(self, state: SchedulingState) -> SchedulingState:
        """Calculate optimal delivery time window in IST."""
        try:
            order_data = state["order_data"]
            
            # Parse estimated ready time (could be in various formats)
            estimated_ready_str = order_data["estimated_ready"]
            estimated_ready = tz_manager.parse_from_storage(estimated_ready_str)
            
            # Add buffer time after food is ready
            delivery_start = tz_manager.add_minutes(estimated_ready, self.prep_buffer_minutes)
            delivery_end = tz_manager.add_minutes(delivery_start, self.delivery_window_minutes)
            preferred_time = tz_manager.add_minutes(delivery_start, 10)  # 10 min into window
            
            state["delivery_window"] = {
                "start_time": tz_manager.format_for_storage(delivery_start),
                "end_time": tz_manager.format_for_storage(delivery_end),
                "preferred_time": tz_manager.format_for_storage(preferred_time),
                "display_start": tz_manager.format_for_display(delivery_start),
                "display_end": tz_manager.format_for_display(delivery_end),
                "display_preferred": tz_manager.format_for_display(preferred_time)
            }
            
            self.logger.info(f"Calculated delivery window: {state['delivery_window']['display_start']} - {state['delivery_window']['display_end']}")
            state["current_node"] = "calculate_delivery_window"
            return state
            
        except Exception as e:
            state["error_context"] = {
                "node": "calculate_delivery_window",
                "error": f"Failed to calculate delivery window: {e}"
            }
            return state
            
    async def _schedule_delivery(self, state: SchedulingState) -> SchedulingState:
        """Schedule the delivery - simplified without calendar integration."""
        try:
            order_data = state["order_data"]
            delivery_window = state["delivery_window"]
            
            # Use preferred time from delivery window
            selected_time = delivery_window["preferred_time"]
            state["selected_time_slot"] = selected_time
            
            state["schedule_result"] = {
                "success": True,
                "delivery_time": selected_time,
                "delivery_window": delivery_window
            }
            
            self.logger.info(f"Successfully scheduled delivery for order {order_data['order_id']} at {selected_time}")
            state["current_node"] = "send_confirmation"
            return state
            
        except Exception as e:
            state["error_context"] = {
                "node": "schedule_delivery",
                "error": f"Failed to schedule delivery: {e}"
            }
            return state
            
    async def _send_confirmation(self, state: SchedulingState) -> SchedulingState:
        """Send confirmation message back to ordering agent."""
        try:
            incoming_message = state["incoming_message"]
            schedule_result = state["schedule_result"]
            order_data = state["order_data"]
            
            confirmation_data = {
                "order_id": order_data["order_id"],
                "delivery_time": schedule_result["delivery_time"],
                "delivery_window": state["delivery_window"]
            }
            
            outgoing_message = self.message_bus.create_schedule_confirmed_message(
                from_agent=self.agent_id,
                to_agent=incoming_message.from_agent,
                schedule_data=confirmation_data,
                correlation_id=incoming_message.correlation_id
            )
            
            state["outgoing_message"] = outgoing_message
            self.logger.info(f"Sent scheduling confirmation for order {order_data['order_id']}")
            return state
            
        except Exception as e:
            state["error_context"] = {
                "node": "send_confirmation",
                "error": f"Failed to send confirmation: {e}"
            }
            return state
            
    async def _handle_scheduling_error(self, state: SchedulingState) -> SchedulingState:
        """Handle scheduling errors and send failure message."""
        incoming_message = state["incoming_message"]
        error_context = state["error_context"]
        order_data = state["order_data"]
        
        failure_data = {
            "order_id": order_data.get("order_id", "unknown"),
            "reason": error_context.get("error", "Unknown scheduling error"),
            "retry_possible": True
        }
        
        outgoing_message = self.message_bus.create_schedule_failed_message(
            from_agent=self.agent_id,
            to_agent=incoming_message.from_agent,
            failure_data=failure_data,
            correlation_id=incoming_message.correlation_id
        )
        
        state["outgoing_message"] = outgoing_message
        self.logger.error(f"Scheduling failed for order {order_data.get('order_id')}: {error_context.get('error')}")
        return state
        
    def _create_error_message(self, original_message: A2AMessage, error: str) -> A2AMessage:
        """Create error message for workflow failures."""
        return self.message_bus.create_schedule_failed_message(
            from_agent=self.agent_id,
            to_agent=original_message.from_agent,
            failure_data={
                "order_id": original_message.payload.get("order_id", "unknown"),
                "reason": f"Workflow error: {error}",
                "retry_possible": False
            },
            correlation_id=original_message.correlation_id
        )
        
    def get_capabilities(self) -> list:
        """Return list of scheduling agent capabilities."""
        return [
            "delivery_scheduling",
            "time_optimization",
            "email_notifications",
            "order_coordination"
        ]
        
    def process_request(self, user_input: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process scheduling request - not used directly, use process_order_message instead."""
        return {
            "status": "info",
            "message": "Scheduling agent processes A2A messages. Use process_order_message() method.",
            "capabilities": self.get_capabilities()
        }
        
    async def cleanup(self):
        """Cleanup resources."""
        self.logger.info("Scheduling agent cleanup completed")
    
    async def process_a2a_message(self, message):
        """Process A2A message from business dashboard"""
        try:
            self.logger.info(f"Processing A2A message: {message.type}")
            
            if message.type == "status_update":
                action = message.payload.get("action")
                
                if action == "order_confirmed":
                    await self._send_order_confirmed_email(message.payload)
                elif action == "order_ready":
                    await self._send_order_ready_email(message.payload)
                    
                self.logger.info(f"A2A message processed successfully: {action}")
            else:
                self.logger.warning(f"Unknown A2A message type: {message.type}")
                
        except Exception as e:
            self.logger.error(f"Error processing A2A message: {e}")
    
    async def _send_order_confirmed_email(self, message_data: dict):
        """Send order confirmation email with calculated delivery time."""
        try:
            order_id = message_data.get("order_id")
            customer_email = message_data.get("customer_email")
            order_data = message_data.get("order_data", {})
            
            # Calculate delivery time (simple implementation)
            from datetime import datetime, timedelta
            delivery_time = datetime.now() + timedelta(minutes=30)  # 30 min delivery
            order_data["estimated_delivery"] = delivery_time.strftime("%I:%M %p")
            
            free_email_service.send_order_accepted_email(customer_email, order_data)
            self.logger.info(f"Order confirmation email sent to {customer_email} for order {order_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to send order confirmation email: {e}")
    
    async def _send_order_ready_email(self, message_data: dict):
        """Send order ready email."""
        try:
            order_id = message_data.get("order_id")
            customer_email = message_data.get("customer_email")
            order_data = message_data.get("order_data", {})
            
            free_email_service.send_pizza_ready_email(customer_email, order_data)
            self.logger.info(f"Order ready email sent to {customer_email} for order {order_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to send order ready email: {e}")
