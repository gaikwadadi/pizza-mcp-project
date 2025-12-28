"""
Pizza ordering agent using LangGraph for state management and natural language processing.
"""
import asyncio
import json
import os
from typing import Dict, Any, List, Optional, TypedDict
from datetime import datetime, timedelta

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledStateGraph

from .agent_base import AgentBase
from .communication import A2AMessage, A2AMessageType, A2AMessageBus
from .session_manager import SessionManager, SessionState, Cart, CartItem, OrderState, ConversationContext, OrderHistory
from .intelligent_clarifier import IntelligentClarifier, ClarificationContext
from .smart_error_handler import SmartErrorHandler, ErrorContext
from utils.timezone_utils import tz_manager
from mcp_clients.pizza_client import PizzaMCPClient, MCPResponse

# Intent Recognition System (Industry Best Practice)
class IntentClassifier:
    """Classify user intents for better conversation handling."""
    
    INTENTS = {
        'cancel': ['cancel', 'abort', 'stop', 'nevermind', 'forget it', 'no thanks', 'quit'],
        'confirm': ['yes', 'confirm', 'proceed', 'ok', 'sure', 'go ahead', 'place order'],
        'deny': ['no', 'nope', 'not now', 'maybe later'],
        'add_to_cart': ['add', 'more', 'another', 'also want', 'plus', 'include'],
        'remove_from_cart': ['remove', 'delete', 'take out', 'minus', 'drop'],
        'modify_order': ['change', 'modify', 'update', 'edit', 'different'],
        'show_cart': ['cart', 'order summary', 'what do i have', 'my order'],
        'show_menu': ['menu', 'options', 'what do you have', 'show me', 'list'],
        'help': ['help', 'what can you do', 'commands', 'options']
    }
    
    @classmethod
    def classify_intent(cls, user_input: str, order_state: str = None) -> str:
        """Classify user intent based on input and current state."""
        user_input_lower = user_input.lower().strip()
        
        # Context-aware intent classification
        if order_state == 'pending_confirmation':
            # In confirmation state, prioritize confirmation/cancellation
            if any(keyword in user_input_lower for keyword in cls.INTENTS['confirm']):
                return 'confirm'
            elif any(keyword in user_input_lower for keyword in cls.INTENTS['cancel']):
                return 'cancel'
            elif any(keyword in user_input_lower for keyword in cls.INTENTS['add_to_cart']):
                return 'add_to_cart'
            elif any(keyword in user_input_lower for keyword in cls.INTENTS['remove_from_cart']):
                return 'remove_from_cart'
        
        # General intent classification
        for intent, keywords in cls.INTENTS.items():
            if any(keyword in user_input_lower for keyword in keywords):
                return intent
        
        return 'order_request'  # Default to order request

# Structured Output Models (Industry Best Practice)
class OrderDetails(BaseModel):
    """Structured model for LLM order extraction."""
    pizza: Optional[str] = Field(None, description="Exact pizza name from menu, null if unclear")
    size: Optional[str] = Field(None, description="Size: small, medium, or large")
    quantity: Optional[int] = Field(None, description="Number of pizzas, default 1 if not specified")
    customer_email: Optional[str] = Field(None, description="Customer email address for order updates")
    special_instructions: Optional[str] = Field(None, description="Any special requests")
    confidence: float = Field(description="Confidence score 0.0-1.0")
    missing_info: List[str] = Field(default_factory=list, description="List of missing required information")
    clarification_needed: Optional[str] = Field(None, description="Clarification question for customer")

class ValidationResult(TypedDict):
    """Order validation result."""
    is_valid: bool
    menu_item: Optional[Dict[str, Any]]
    estimated_price: Optional[float]
    warnings: List[str]
    errors: List[str]

class OrderConfirmation(TypedDict):
    """Order confirmation details."""
    order_id: str
    status: str
    prep_time: str
    estimated_ready: str
    total_price: float
    items: List[Dict[str, Any]]

class OrderingState(TypedDict):
    """LangGraph state for ordering workflow."""
    # Input
    user_input: str
    session_id: Optional[str]
    conversation_history: List[Dict[str, str]]
    
    # Processing
    parsed_order: Optional[OrderDetails]
    validation_result: Optional[ValidationResult]
    
    # Output
    order_confirmation: Optional[OrderConfirmation]
    user_response: Optional[str]
    handoff_message: Optional[A2AMessage]
    
    # Control
    current_node: str
    retry_count: int
    error_context: Optional[Dict[str, Any]]

class PizzaOrderingAgent(AgentBase):
    """AI agent for processing pizza orders via natural language."""
    
    def __init__(self):
        """Initialize the pizza ordering agent."""
        # Get temperature with validation
        temp_str = os.getenv("ORDERING_AGENT_TEMPERATURE")
        temperature = None
        if temp_str:
            try:
                temperature = float(temp_str)
            except ValueError:
                raise ValueError(f"ORDERING_AGENT_TEMPERATURE must be a valid number, got: {temp_str}")
        
        super().__init__(
            agent_id="ordering_agent",
            agent_name=os.getenv("ORDERING_AGENT_NAME"),
            model_name=os.getenv("GROQ_MODEL_ID"),
            temperature=temperature
        )
        
        # Initialize structured output parser (Industry Best Practice)
        self.output_parser = PydanticOutputParser(pydantic_object=OrderDetails)
        
        # Initialize session manager for context tracking
        self.session_manager = SessionManager()
        
        # Initialize intelligent systems (Tier 2 improvements)
        self.clarifier = IntelligentClarifier()
        self.error_handler = None  # Will be initialized after menu is loaded
        
        # Initialize MCP client
        self.mcp_client = PizzaMCPClient()
        
        # Build LangGraph workflow
        self.workflow = self._build_workflow()
        
        # Menu cache
        self._menu_cache = None
        self._menu_cache_time = None
        
    def get_capabilities(self) -> List[str]:
        """Return agent capabilities."""
        return [
            "natural_language_order_processing",
            "pizza_menu_browsing", 
            "order_placement",
            "order_tracking",
            "menu_recommendations"
        ]
    
    def _build_workflow(self) -> CompiledStateGraph:
        """Build LangGraph state machine for order processing."""
        workflow = StateGraph(OrderingState)
        
        # Add nodes
        workflow.add_node("understand_order", self._understand_order)
        workflow.add_node("validate_order", self._validate_order)
        workflow.add_node("show_clarification", self._show_clarification_message)
        workflow.add_node("show_confirmation", self._show_confirmation)
        workflow.add_node("place_order", self._place_order)
        workflow.add_node("confirm_order", self._confirm_order)
        workflow.add_node("prepare_handoff", self._prepare_handoff)
        workflow.add_node("collect_email", self._collect_email)
        workflow.add_node("handle_error", self._handle_workflow_error)
        
        # Set entry point
        workflow.set_entry_point("understand_order")
        
        # Add edges
        workflow.add_conditional_edges(
            "understand_order",
            self._should_validate,
            {
                "validate": "validate_order",
                "clarify": "show_clarification",
                "place_order": "place_order",  # Direct route for confirmation responses
                "error": "handle_error"
            }
        )
        
        workflow.add_conditional_edges(
            "validate_order", 
            self._should_show_confirmation,
            {
                "confirm": "show_confirmation",
                "error": "handle_error"
            }
        )
        
        workflow.add_conditional_edges(
            "place_order",
            self._should_confirm,
            {
                "confirm": "confirm_order",
                "error": "handle_error"
            }
        )
        
        workflow.add_edge("confirm_order", "prepare_handoff")
        # Email collection happens after order confirmation, not in main workflow
        workflow.add_edge("show_clarification", END)
        workflow.add_edge("show_confirmation", END)  # End after showing confirmation
        workflow.add_edge("prepare_handoff", END)
        workflow.add_edge("handle_error", END)
        
        return workflow.compile()
    
    async def process_request(self, user_input: str, session_id: str = None, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process user pizza order request with session context."""
        try:
            # Use provided session_id (client_id) for consistent session tracking
            if not session_id:
                session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(user_input) % 100000:05d}"
            
            # Get or create session using the client_id as session_id
            session = self.session_manager.get_or_create_session(session_id)
            
            # CRITICAL: EMAIL COLLECTION CHECK - BEFORE ANY PROCESSING
            if (session.current_order_state == OrderState.RESTAURANT_PENDING and 
                "@" in user_input and "." in user_input):
                
                # Extract email using regex
                import re
                email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                emails = re.findall(email_pattern, user_input)
                
                if emails:
                    customer_email = emails[0]
                    
                    # Store customer email in session and database
                    session.customer_email = customer_email
                    
                    # Update the order in database with customer email
                    if hasattr(session, 'recent_order_id'):
                        await self._update_order_customer_email(session.recent_order_id, customer_email)
                    
                    # Send A2A message to scheduling agent
                    await self._send_email_to_scheduling_agent_direct(session, customer_email)
                    
                    # Update session context
                    session.context.add_message("user", user_input)
                    session.context.add_message("assistant", f"✅ Thank you! We'll send order updates to {customer_email}\n\n🏪 Your order is now with the restaurant. You'll be notified once they accept it!")
                    
                    # Return success response immediately
                    return {
                        "success": True,
                        "session_id": session_id,
                        "response": f"✅ Thank you! We'll send order updates to {customer_email}\n\n🏪 Your order is now with the restaurant. You'll be notified once they accept it!",
                        "order_confirmation": None,
                        "handoff_message": None,
                        "conversation_history": session.context.get_recent_context(),
                        "cart": session.cart.__dict__ if session.cart.items else None,
                        "order_state": session.current_order_state.value
                    }
                
                # Invalid email format
                session.context.add_message("user", user_input)
                session.context.add_message("assistant", "🏪 Your order has been sent to the restaurant for approval.\n⏱️ While we wait, please provide your email address for order updates:")
                
                return {
                    "success": True,
                    "session_id": session_id,
                    "response": "🏪 Your order has been sent to the restaurant for approval.\n⏱️ While we wait, please provide your email address for order updates:",
                    "order_confirmation": None,
                    "handoff_message": None,
                    "conversation_history": session.context.get_recent_context(),
                    "cart": session.cart.__dict__ if session.cart.items else None,
                    "order_state": session.current_order_state.value
                }
            
            # Add user message to conversation history
            session.context.add_message("user", user_input)
            
            # Connect to MCP server
            self.logger.info(f"MCP client connected before check: {self.mcp_client.is_connected()}")
            
            if not self.mcp_client.is_connected():
                self.logger.info("Attempting to connect to MCP server...")
                connected = await self.mcp_client.connect()
                self.logger.info(f"MCP connection result: {connected}")
                
                if not connected:
                    return self.handle_error(
                        Exception("Failed to connect to pizza service"),
                        "mcp_connection"
                    )
            else:
                self.logger.info("MCP client already connected")
            
            # Initialize state with session context
            initial_state = OrderingState(
                user_input=user_input,
                session_id=session_id,
                conversation_history=session.context.get_recent_context(),
                parsed_order=None,
                validation_result=None,
                order_confirmation=None,
                user_response=None,
                handoff_message=None,
                current_node="understand_order",
                retry_count=0,
                error_context=None
            )
            
            # Run workflow
            result = await self.workflow.ainvoke(initial_state)
            
            # DEBUG: Log workflow result
            self.logger.info(f"🔍 Workflow completed with final node: {result.get('current_node')}")
            self.logger.info(f"🔍 User response length: {len(result.get('user_response', ''))}")
            self.logger.info(f"🔍 User response preview: {result.get('user_response', 'None')[:100]}...")
            self.logger.info(f"🔍 Error context: {result.get('error_context')}")
            self.logger.info(f"🔍 All state keys: {list(result.keys())}")
            
            # Update session with assistant response
            if result.get("user_response"):
                session.context.add_message("assistant", result["user_response"])
            
            # Log interaction
            self.log_interaction("order_processed", {
                "user_input": user_input,
                "session_id": session_id,
                "success": result.get("order_confirmation") is not None,
                "final_node": result.get("current_node")
            })
            
            return {
                "success": True,
                "session_id": session_id,
                "response": result.get("user_response", "I'm here to help with your pizza order!"),
                "order_confirmation": result.get("order_confirmation"),
                "handoff_message": result.get("handoff_message"),
                "conversation_history": session.context.get_recent_context(),
                "cart": session.cart.__dict__ if session.cart.items else None,
                "order_state": session.current_order_state.value
            }
            
        except Exception as e:
            return self.handle_error(e, "process_request")
    
    async def _understand_order(self, state: OrderingState) -> OrderingState:
        """Extract order details with intelligent clarification."""
        try:
            self.logger.debug("Starting order understanding...")
            session_id = state.get("session_id")
            session = self.session_manager.get_session(session_id) if session_id else None
            
            # CRITICAL FIX: Check if this is email collection based on conversation context
            if session and session.context.conversation_history:
                last_assistant_msg = None
                for msg in reversed(session.context.conversation_history):
                    if msg.get("role") == "assistant":
                        last_assistant_msg = msg.get("content", "")
                        break
                
                # If last message asked for email and user provided email
                if (last_assistant_msg and "email address for order updates" in last_assistant_msg):
                    user_input = state.get("user_input", "")
                    if "@" in user_input and "." in user_input:
                        import re
                        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                        emails = re.findall(email_pattern, user_input)
                        if emails:
                            # Use email immediately, don't store
                            customer_email = emails[0]
                            state["user_response"] = f"✅ Thank you! We'll send order updates to {customer_email}\n\n🏪 Your order is now with the restaurant. You'll be notified once they accept it!"
                            state["current_node"] = "understand_order"
                            
                            # Send email to scheduling agent via A2A message
                            await self._send_email_to_scheduling_agent(state, customer_email)
                            return state
                    
                    # Invalid email provided
                    state["user_response"] = "🏪 Your order has been sent to the restaurant for approval.\n⏱️ While we wait, please provide your email address for order updates:"
                    state["current_node"] = "understand_order"
                    return state
            
            # Simple cancellation check (original logic)
            user_input = state["user_input"].lower().strip()
            if self._is_cancellation_request(user_input) and session:
                return await self._handle_cancellation_request(state, session)
            
            # Get menu for context
            menu = await self._get_menu_cached()
            menu_items = [item["name"] for item in menu] if menu else []
            self.logger.debug(f"Menu items loaded: {len(menu_items)}")
            
            # Initialize error handler with menu items
            if not self.error_handler:
                self.error_handler = SmartErrorHandler(menu_items)
            
            # Update session context with mentioned items
            if session:
                session.context.extract_mentioned_items(state["user_input"], menu_items)
            
            # Create enhanced prompt with conversation context
            system_prompt = self._create_context_aware_prompt(menu_items, session)
            
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=state["user_input"])
            ]
            
            self.logger.debug("Calling LLM...")
            response = await self.llm.ainvoke(messages)
            self.logger.debug("LLM call completed")
            
            # Debug the actual response structure
            self.logger.debug(f"Raw LLM response: {response}")
            self.logger.debug(f"Response type: {type(response)}")
            if hasattr(response, 'content'):
                self.logger.debug(f"Response content: {response.content}")
                self.logger.debug(f"Content type: {type(response.content)}")
            
            self.logger.debug("Starting response parsing...")
            # Parse LLM response
            try:
                # Extract text content from various response formats
                content = response.content
                
                if isinstance(content, list):
                    # New format: [{'type': 'text', 'text': '...'}]
                    if content and isinstance(content[0], dict) and 'text' in content[0]:
                        content = content[0]['text']
                    else:
                        content = str(content[0]) if content else ""
                elif not isinstance(content, str):
                    content = str(content)
                
                # Use structured output parser for robust parsing (Industry Best Practice)
                order_details = self.output_parser.parse(content)
                
                # Check if user provided email in their message
                user_input = state.get("user_input", "").lower()
                if "@" in user_input and "." in user_input:
                    # Extract email from user input
                    import re
                    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                    emails = re.findall(email_pattern, state.get("user_input", ""))
                    if emails:
                        order_details.customer_email = emails[0]
                        self.logger.info(f"Extracted email from user input: {emails[0]}")
                
                # REMOVED: Email collection during order process
                # Email will be collected after order submission
                self.logger.debug(f"Parsed order details: {order_details}")
                
            except Exception as e:
                # Enhanced error handling with smart recovery
                self.logger.error(f"Structured parsing failed: {e}")
                
                if session and self.error_handler:
                    error_context = ErrorContext(
                        error_type="parsing_failed",
                        user_input=state["user_input"],
                        attempted_action="order_parsing",
                        conversation_context=session.context.get_recent_context()
                    )
                    recovery_message = self.error_handler.handle_error(error_context)
                    state["user_response"] = recovery_message
                else:
                    state["user_response"] = "I'm experiencing technical difficulties connecting to our ordering system. Please try again in a moment."
                
                return state
            
            state["parsed_order"] = order_details
            state["current_node"] = "understand_order"
            
            return state
            
        except Exception as e:
            self.logger.error(f"LLM processing failed: {e}")
            return self.handle_error(e, "understand_order")
    
    async def _validate_order(self, state: OrderingState) -> OrderingState:
        """Validate parsed order and create cart for confirmation."""
        try:
            parsed_order = state["parsed_order"]
            session_id = state.get("session_id")
            
            if not parsed_order:
                state["error_context"] = {"node": "validate_order", "error": "No parsed order"}
                return state
            
            # Get session for cart management
            session = self.session_manager.get_session(session_id) if session_id else None
            
            # Check if we need to add pending multi-pizza to cart - REMOVED
            # This logic is no longer needed as we process all pizzas immediately
            
            # Get menu
            menu = await self._get_menu_cached()
            if not menu:
                state["error_context"] = {"node": "validate_order", "error": "Menu unavailable"}
                state["response"] = "I'm having trouble accessing our menu right now. Please try again in a moment."
                return state
            
            # Extract menu items for validation
            menu_items = [item["name"] for item in menu] if menu else []
            
            # Check if order has minimum required info (confidence > 0.7 or complete info)
            if (parsed_order.confidence or 0) < 0.7:
                # Use intelligent clarification instead of generic message
                if session and self.clarifier:
                    clarification_context = ClarificationContext(
                        user_input=state["user_input"],
                        conversation_history=session.context.get_recent_context(),
                        mentioned_items=session.context.mentioned_items,
                        menu_items=menu_items,
                        last_intent=session.context.current_intent
                    )
                    intelligent_clarification = self.clarifier.generate_clarification(clarification_context)
                    state["user_response"] = intelligent_clarification
                elif parsed_order.clarification_needed:
                    state["user_response"] = parsed_order.clarification_needed
                else:
                    state["user_response"] = "What would you like to order today?"
                
                state["validation_result"] = ValidationResult(
                    is_valid=False,
                    menu_item=None,
                    estimated_price=None,
                    warnings=[],
                    errors=["Needs clarification"]
                )
                return state
            
            # Check for MULTI_ORDER processing
            if parsed_order.pizza == "MULTI_ORDER" and parsed_order.special_instructions and parsed_order.special_instructions.startswith("PIZZAS:"):
                # Process multiple pizzas immediately
                pizzas_data = parsed_order.special_instructions.replace("PIZZAS:", "")
                pizza_items = pizzas_data.split(",")
                
                # Clear existing cart for new multi-order
                if session:
                    session.cart.clear()
                
                all_valid = True
                total_estimated_price = 0
                
                for pizza_item in pizza_items:
                    parts = pizza_item.split(":")
                    if len(parts) >= 3:
                        pizza_name = parts[0]
                        size = parts[1]
                        quantity = int(parts[2]) if parts[2].isdigit() else 1
                        
                        # Find menu item
                        menu_item = None
                        for item in menu:
                            if item["name"].lower() == pizza_name.lower():
                                menu_item = item
                                break
                        
                        if menu_item and size in menu_item.get("sizes", []):
                            # Calculate price
                            base_price = menu_item["price"]
                            size_multiplier = {"small": 0.8, "medium": 1.0, "large": 1.2}.get(size, 1.0)
                            item_price = round(base_price * size_multiplier * quantity)
                            total_estimated_price += item_price
                            
                            # Add to cart
                            if session:
                                cart_item = CartItem(
                                    pizza=pizza_name,
                                    size=size,
                                    quantity=quantity,
                                    base_price=base_price,
                                    size_multiplier=size_multiplier,
                                    total_price=item_price,
                                    special_instructions=None
                                )
                                session.cart.add_item(cart_item)
                        else:
                            all_valid = False
                            errors.append(f"Invalid pizza or size: {pizza_name} ({size})")
                
                if all_valid and session and session.cart.items:
                    # Set session state
                    session.current_order_state = OrderState.PENDING_CONFIRMATION
                    
                    validation_result = ValidationResult(
                        is_valid=True,
                        menu_item={"name": "Multi-Order", "price": total_estimated_price},
                        estimated_price=total_estimated_price,
                        warnings=[],
                        errors=[]
                    )
                    
                    state["validation_result"] = validation_result
                    state["current_node"] = "validate_order"
                    return state
                else:
                    validation_result = ValidationResult(
                        is_valid=False,
                        menu_item=None,
                        estimated_price=None,
                        warnings=[],
                        errors=errors or ["Multi-order processing failed"]
                    )
                    state["validation_result"] = validation_result
                    return state
            
            # Apply smart defaults - REMOVED DEFAULT SIZE
            pizza_name = parsed_order.pizza
            size = parsed_order.size  # No default - must be explicitly provided
            quantity = parsed_order.quantity or 1  # Default to 1
            
            # Find matching menu item
            menu_item = None
            for item in menu:
                if item["name"].lower() == pizza_name.lower():
                    menu_item = item
                    break
            
            # Validate - REQUIRE SIZE TO BE SPECIFIED
            errors = []
            warnings = []
            
            if not menu_item:
                errors.append(f"Pizza '{pizza_name}' not found in menu")
                self.logger.error(f"Validation error: Pizza '{pizza_name}' not found in menu")
            elif not size:
                errors.append("Size must be specified (small, medium, or large)")
                self.logger.error(f"Validation error: Size not specified for {pizza_name}")
            elif size not in menu_item.get("sizes", []):
                errors.append(f"Size '{size}' not available for {pizza_name}")
                self.logger.error(f"Validation error: Size '{size}' not available for {pizza_name}. Available sizes: {menu_item.get('sizes', [])}")
            
            if quantity < 1 or quantity > 10:
                errors.append("Quantity must be between 1 and 10")
                self.logger.error(f"Validation error: Invalid quantity {quantity}")
            
            self.logger.info(f"Validation check: pizza='{pizza_name}', size='{size}', quantity={quantity}, menu_item_found={menu_item is not None}, errors={errors}")
            
            # Calculate price - ONLY if both pizza and size are valid
            estimated_price = None
            if menu_item and size and not errors:
                base_price = menu_item["price"]
                size_multiplier = {"small": 0.8, "medium": 1.0, "large": 1.2}.get(size, 1.0)
                estimated_price = round(base_price * size_multiplier * quantity)
                
                # Create cart item if session exists
                if session:
                    cart_item = CartItem(
                        pizza=pizza_name,
                        size=size,
                        quantity=quantity,
                        base_price=base_price,
                        size_multiplier=size_multiplier,
                        total_price=estimated_price,
                        special_instructions=parsed_order.special_instructions
                    )
                    
                    # Check if we're adding to existing cart or creating new order
                    if session.confirmation_pending:
                        # Add to existing cart
                        session.cart.add_item(cart_item)
                    else:
                        # Clear existing cart and add new item (new order)
                        session.cart.clear()
                        session.cart.add_item(cart_item)
                    session.current_order_state = OrderState.PENDING_CONFIRMATION
            
            validation_result = ValidationResult(
                is_valid=len(errors) == 0,
                menu_item=menu_item,
                estimated_price=estimated_price,
                warnings=warnings,
                errors=errors
            )
            
            state["validation_result"] = validation_result
            state["current_node"] = "validate_order"
            
            return state
            
        except Exception as e:
            self.logger.error(f"Order validation failed: {e}")
            return self.handle_error(e, "validate_order")
    
    async def _show_confirmation(self, state: OrderingState) -> OrderingState:
        """Show order confirmation with cart details before placing order."""
        try:
            self.logger.info("_show_confirmation method called")
            session_id = state.get("session_id")
            session = self.session_manager.get_session(session_id) if session_id else None
            
            self.logger.info(f"Session found: {session is not None}")
            if session:
                self.logger.info(f"Cart items count: {len(session.cart.items) if session.cart else 0}")
            
            if not session or not session.cart.items:
                self.logger.error("No session or cart items found")
                state["error_context"] = {"node": "show_confirmation", "error": "No cart items"}
                return state
            
            cart = session.cart
            self.logger.info(f"Cart assigned: {cart}")
            self.logger.info(f"Cart total: {cart.total}, prep time: {cart.estimated_prep_time}")
            
            self.logger.info("Using timezone manager for delivery calculations")
            
            # Calculate delivery time
            prep_time_minutes = cart.estimated_prep_time
            self.logger.info(f"Getting delivery time for {prep_time_minutes} minutes")
            delivery_time = tz_manager.add_minutes(tz_manager.now_local(), prep_time_minutes)
            delivery_display = tz_manager.format_delivery_time_friendly(delivery_time)
            self.logger.info(f"Delivery time calculated: {delivery_display}")
            
            # Build confirmation message
            self.logger.info("Building confirmation message...")
            confirmation_parts = ["🛒 Order Summary\n"]
            
            for i, item in enumerate(cart.items, 1):
                item_line = f"{i}. {item.pizza} ({item.size}) x{item.quantity} - Rs.{item.total_price:.0f}"
                confirmation_parts.append(item_line)
                # Don't show technical multi-pizza notes to user
                if item.special_instructions and not item.special_instructions.startswith("MULTI_PIZZA:"):
                    confirmation_parts.append(f"   Note: {item.special_instructions}")
            
            self.logger.info(f"Added {len(cart.items)} items to confirmation")
            
            confirmation_parts.extend([
                f"\nSubtotal: Rs.{cart.subtotal:.0f}",
                f"Delivery Fee: Rs.{cart.delivery_fee:.0f}" if cart.delivery_fee > 0 else "Delivery: FREE",
                f"Total: Rs.{cart.total:.0f}",
                f"\nEstimated Delivery: {delivery_display}",
                f"Preparation Time: {prep_time_minutes} minutes"
            ])
            
            confirmation_parts.append("\nWould you like to confirm this order? Reply 'yes' to submit to restaurant or 'no' to cancel.")
            
            confirmation_message = "\n".join(confirmation_parts)
            self.logger.info(f"Confirmation message built: {len(confirmation_message)} characters")
            
            # Set session to pending confirmation
            session.confirmation_pending = True
            session.current_order_state = OrderState.PENDING_CONFIRMATION
            self.logger.info("Session state updated to pending confirmation")
            
            state["user_response"] = confirmation_message
            state["current_node"] = "show_confirmation"
            
            self.logger.info("_show_confirmation completed successfully")
            return state
            
        except Exception as e:
            self.logger.error(f"Confirmation display failed: {e}")
            self.logger.error(f"Exception type: {type(e)}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return self.handle_error(e, "show_confirmation")
    
    async def _place_order(self, state: OrderingState) -> OrderingState:
        """Place order via MCP server."""
        try:
            parsed_order = state.get("parsed_order")
            validation_result = state.get("validation_result")
            
            # For confirmation responses, we don't have validation_result but we have session cart
            session_id = state.get("session_id")
            session = self.session_manager.get_session(session_id) if session_id else None
            
            if not parsed_order and not (session and session.cart.items):
                state["error_context"] = {"node": "place_order", "error": "No order to place"}
                return state
            
            # If we have validation_result, check it. Otherwise, trust the session cart (confirmation case)
            if validation_result and not validation_result.get("is_valid"):
                state["error_context"] = {"node": "place_order", "error": "Invalid order"}
                return state
            
            # For confirmation responses, get order details from cart
            if session and session.cart.items:
                # Create single order with all cart items
                cart_items = []
                for cart_item in session.cart.items:
                    cart_items.append({
                        "pizza": cart_item.pizza,
                        "size": cart_item.size,
                        "quantity": cart_item.quantity,
                        "price": cart_item.base_price
                    })
                
                # Call MCP server with all items
                mcp_response = await self.mcp_client.create_order(
                    items=cart_items,
                    customer_email=getattr(session, 'customer_email', None)
                )
                
                if mcp_response.success:
                    order_data = mcp_response.data
                    # Store recent order ID for email updates
                    session.recent_order_id = order_data.get('order_id')
                    
                    # Store customer email for this order if available
                    if hasattr(session, 'customer_email') and session.customer_email:
                        await self._store_customer_email(order_data.get('order_id'), session.customer_email)
                else:
                    state["error_context"] = {"node": "place_order", "error": f"Backend error: {mcp_response.error}"}
                    return state
            else:
                # Single item order (legacy path)
                pizza_name = parsed_order.pizza if parsed_order else "Unknown"
                size = parsed_order.size if parsed_order else "medium"
                quantity = parsed_order.quantity if parsed_order else 1
                
                # Call MCP server with single item as array
                single_item = [{
                    "pizza": pizza_name,
                    "size": size,
                    "quantity": quantity,
                    "price": 0  # Will be set by backend
                }]
                
                mcp_response = await self.mcp_client.create_order(
                    items=single_item,
                    customer_email=getattr(session, 'customer_email', None)
                )
                
                if not mcp_response.success:
                    state["error_context"] = {"node": "place_order", "error": mcp_response.error}
                    return state
                
                order_data = mcp_response.data
                
                # Store customer email for this order if available
                if hasattr(session, 'customer_email') and session.customer_email:
                    await self._store_customer_email(order_data.get('order_id'), session.customer_email)
            estimated_ready = datetime.now() + timedelta(minutes=20)  # Default prep time
            session_id = state.get("session_id")
            session = self.session_manager.get_session(session_id) if session_id else None
            
            # Create order history entry
            if session:
                order_history = OrderHistory(
                    order_id=order_data.get("order_id", "unknown"),
                    items=session.cart.items.copy(),
                    total=session.cart.total,
                    status=OrderState.CONFIRMED,
                    created_at=datetime.now(),
                    confirmed_at=datetime.now()
                )
                session.add_to_history(order_history)
                session.current_order_state = OrderState.CONFIRMED
            
            # Get total price from validation result or cart
            if validation_result and validation_result.get("estimated_price"):
                total_price = validation_result["estimated_price"]
            elif session and session.cart.items:
                total_price = session.cart.total
            else:
                total_price = 0.0
            
            # Use consistent delivery time from cart calculation
            prep_time_minutes = session.cart.estimated_prep_time if session else 20
            delivery_time = tz_manager.add_minutes(tz_manager.now_local(), prep_time_minutes)
            estimated_ready = tz_manager.format_for_storage(delivery_time)  # Use ISO format for scheduling agent
            
            # Create items list from cart for multi-item orders
            items_list = []
            if session and session.cart.items:
                for item in session.cart.items:
                    items_list.append({
                        "pizza": item.pizza,
                        "size": item.size,
                        "quantity": item.quantity
                    })
            else:
                items_list = [{
                    "pizza": pizza_name,
                    "size": size,
                    "quantity": quantity
                }]
            
            order_confirmation = OrderConfirmation(
                order_id=order_data.get("order_id", "unknown"),
                status=order_data.get("status", "preparing"),
                prep_time=order_data.get("prep_time", "20 mins"),
                estimated_ready=estimated_ready,
                total_price=total_price,
                items=items_list
            )
            
            state["order_confirmation"] = order_confirmation
            state["current_node"] = "place_order"
            
            return state
            
        except Exception as e:
            self.logger.error(f"Place order failed: {e}")
            self.logger.error(f"Exception type: {type(e)}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return self.handle_error(e, "place_order")
    
    async def _confirm_order(self, state: OrderingState) -> OrderingState:
        """Format confirmation response for user and transition to email collection."""
        try:
            order_confirmation = state["order_confirmation"]
            if not order_confirmation:
                state["error_context"] = {"node": "confirm_order", "error": "No order confirmation"}
                return state
            
            # Get session for state management
            session_id = state.get("session_id")
            session = self.session_manager.get_session(session_id) if session_id else None
            
            # Format user response with all items
            total_price = order_confirmation.get('total_price', 0)
            items = order_confirmation.get('items', [])
            
            response_parts = [
                "✅ Order Submitted to Restaurant!",
                f"\nOrder ID: {order_confirmation['order_id']}"
            ]
            
            # Add all items to confirmation
            if len(items) > 1:
                response_parts.append("Items:")
                for item in items:
                    response_parts.append(f"- {item['pizza']} ({item['size']}) x{item['quantity']}")
            else:
                item = items[0] if items else {}
                response_parts.extend([
                    f"Pizza: {item.get('pizza', 'Unknown')} ({item.get('size', 'Unknown')})",
                    f"Quantity: {item.get('quantity', 1)}"
                ])
            
            response_parts.extend([
                f"Total: Rs.{total_price:.0f}",
                f"\n🏪 Your order has been sent to the restaurant for approval.",
                f"⏱️ While we wait, please provide your email address for order updates:"
            ])
            
            response = "\n".join(response_parts)
            
            # Update session state - no email storage needed
            if session:
                session.current_order_state = OrderState.RESTAURANT_PENDING
                # Remove: session.pending_email_collection = True
            
            state["user_response"] = response
            state["current_node"] = "confirm_order"
            
            return state
            
        except Exception as e:
            return self.handle_error(e, "confirm_order")
    
    async def _prepare_handoff(self, state: OrderingState) -> OrderingState:
        """Prepare A2A message for scheduling agent."""
        try:
            order_confirmation = state["order_confirmation"]
            if not order_confirmation:
                return state
            
            # Initialize message bus
            message_bus = A2AMessageBus()
            
            # Prepare order data for scheduling agent (no email stored)
            order_data = {
                "order_id": order_confirmation["order_id"],
                "prep_time": order_confirmation["prep_time"],
                "estimated_ready": order_confirmation["estimated_ready"],
                "customer_info": {
                    "name": "Customer"
                    # No email here - will be sent separately when collected
                },
                "items": order_confirmation["items"],
                "total_price": order_confirmation["total_price"],
                "status": "restaurant_pending"
            }
            
            # Create A2A message using new protocol
            handoff_message = message_bus.create_order_placed_message(
                from_agent=self.agent_id,
                to_agent="scheduling_agent",
                order_data=order_data,
                correlation_id=self.session_id
            )
            
            state["handoff_message"] = handoff_message
            state["current_node"] = "prepare_handoff"
            
            return state
            
        except Exception as e:
            return self.handle_error(e, "prepare_handoff")
    
    async def _show_clarification_message(self, state: OrderingState) -> OrderingState:
        """Show clarification message from LLM to user."""
        try:
            parsed_order = state.get("parsed_order")
            if parsed_order and parsed_order.clarification_needed:
                state["user_response"] = parsed_order.clarification_needed
            else:
                state["user_response"] = "What would you like to order today?"
            
            state["current_node"] = "show_clarification"
            return state
            
        except Exception as e:
            return self.handle_error(e, "show_clarification")
    
    async def _collect_email(self, state: OrderingState) -> OrderingState:
        """Collect email address after order submission."""
        try:
            session_id = state.get("session_id")
            session = self.session_manager.get_session(session_id) if session_id else None
            
            if not session or not hasattr(session, 'pending_email_collection'):
                # No email collection needed, proceed
                state["current_node"] = "collect_email"
                return state
            
            # Check if this is an email input
            user_input = state.get("user_input", "")
            if "@" in user_input and "." in user_input:
                # Extract email
                import re
                email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                emails = re.findall(email_pattern, user_input)
                
                if emails:
                    # Store email in session
                    session.customer_email = emails[0]
                    session.pending_email_collection = False
                    
                    state["user_response"] = f"✅ Thank you! We'll send order updates to {emails[0]}\n\n🏪 Your order is now with the restaurant. You'll be notified once they accept it!"
                    state["current_node"] = "collect_email"
                    
                    self.logger.info(f"Email collected for order: {emails[0]}")
                    return state
            
            # Invalid or no email provided
            state["user_response"] = "🏪 Your order has been sent to the restaurant for approval.\n⏱️ While we wait, please provide your email address for order updates:"
            state["current_node"] = "collect_email"
            
            return state
            
        except Exception as e:
            return self.handle_error(e, "collect_email")
    
    async def _send_email_to_scheduling_agent_direct(self, session, customer_email: str):
        """Send customer email directly to scheduling agent for notifications."""
        try:
            # Create email data from session cart
            email_data = {
                "order_id": f"email_{session.session_id[-8:]}",
                "customer_email": customer_email,
                "action": "email_collected",
                "items": [{"pizza": item.pizza, "size": item.size, "quantity": item.quantity} for item in session.cart.items],
                "total_price": session.cart.total
            }
            
            # Create A2A message
            from agents.communication import A2AMessage, A2AMessageType
            message = A2AMessage(
                type=A2AMessageType.STATUS_UPDATE,
                from_agent=self.agent_id,
                to_agent="scheduling_agent",
                payload=email_data,
                correlation_id=session.session_id
            )
            
            self.logger.info(f"Email sent to scheduling agent via A2A: {customer_email}")
            
        except Exception as e:
            self.logger.error(f"Failed to send email to scheduling agent: {e}")
    
    async def _store_customer_email(self, order_id: str, customer_email: str):
        """Store customer email in business dashboard for notifications."""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                await session.post(
                    f"http://localhost:8090/api/orders/{order_id}/email",
                    json={"customer_email": customer_email}
                )
            self.logger.info(f"Stored customer email for order {order_id}: {customer_email}")
        except Exception as e:
            self.logger.error(f"Failed to store customer email: {e}")
    
    async def _send_email_to_scheduling_agent(self, state: OrderingState, customer_email: str):
        """Send customer email to scheduling agent for notifications."""
        try:
            # Get order confirmation from state
            session_id = state.get("session_id")
            session = self.session_manager.get_session(session_id) if session_id else None
            
            if not session or not session.cart.items:
                return
            
            # Get the last order ID from conversation or generate one
            order_id = f"email_update_{session_id[-8:]}"
            
            # Initialize message bus
            from agents.communication import A2AMessageBus, A2AMessage, A2AMessageType
            message_bus = A2AMessageBus()
            
            # Create email update message using correct A2A API
            email_data = {
                "order_id": order_id,
                "customer_email": customer_email,
                "action": "email_collected",
                "items": [{"pizza": item.pizza, "size": item.size, "quantity": item.quantity} for item in session.cart.items],
                "total_price": session.cart.total
            }
            
            # Create A2A message directly (no create_message method exists)
            message = A2AMessage(
                type=A2AMessageType.STATUS_UPDATE,
                from_agent=self.agent_id,
                to_agent="scheduling_agent",
                payload=email_data,
                correlation_id=session_id
            )
            
            self.logger.info(f"Email sent to scheduling agent: {customer_email}")
            
        except Exception as e:
            self.logger.error(f"Failed to send email to scheduling agent: {e}")
    
    async def _handle_workflow_error(self, state: OrderingState) -> OrderingState:
        """Handle workflow errors."""
        error_context = state.get("error_context") or {}
        error_node = error_context.get("node", "unknown")
        error_message = error_context.get("error", "Unknown error")
        
        # Check if we have a parsed order with clarification needed
        parsed_order = state.get("parsed_order")
        if parsed_order and parsed_order.clarification_needed:
            response = parsed_order.clarification_needed
        elif error_node == "understand_order":
            # Check if we have a specific response from the error handling
            if state.get("response"):
                response = state["response"]
            else:
                response = "I'm experiencing technical difficulties connecting to our ordering system. Please try again in a moment."
        elif error_node == "validate_order":
            response = f"There's an issue with your order: {error_message}. Please check our menu and try again."
        elif error_node == "place_order":
            response = "I'm sorry, there was a problem placing your order. Please try again in a moment."
        else:
            response = "I apologize, but I encountered an error processing your request. Please try again."
        
        state["user_response"] = response
        state["current_node"] = "show_clarification"
        
        return state
    
    def _should_show_confirmation(self, state: OrderingState) -> str:
        """Determine if order should show confirmation."""
        self.logger.info(f"_should_show_confirmation called with state keys: {list(state.keys())}")
        
        if state.get("error_context"):
            self.logger.info(f"Found error_context: {state.get('error_context')}")
            return "error"
            
        validation_result = state.get("validation_result")
        self.logger.info(f"Validation result: {validation_result}")
        
        if validation_result and validation_result.get("is_valid"):
            # FIXED: Always confirm valid orders, no email requirement
            self.logger.info("Validation is valid, returning 'confirm'")
            return "confirm"
            
        self.logger.info("Validation not valid, returning 'error'")
        return "error"
    
    def _should_validate(self, state: OrderingState) -> str:
        """Determine if order should be validated."""
        if state.get("error_context"):
            return "error"
            
        parsed_order = state.get("parsed_order")
        if not parsed_order:
            return "error"
        
        # Get session and user input for cart editing checks
        user_input = state.get("user_input", "").lower().strip()
        session_id = state.get("session_id")
        session = self.session_manager.get_session(session_id) if session_id else None
        
        # Email collection is now handled in understand_order via context - remove old logic
        
        # Check if this is a cancellation request
        if parsed_order and parsed_order.pizza == "CANCEL_REQUEST":
            if session:
                session.pending_cancellation = True
            return "clarify"  # Show cancellation confirmation
        
        # Check if user is confirming cancellation
        if (session and hasattr(session, 'pending_cancellation') and session.pending_cancellation and 
            user_input in ["yes", "y", "confirm", "ok"]):
            # User confirmed cancellation
            session.cart.clear()
            session.current_order_state = OrderState.CANCELLED
            session.confirmation_pending = False
            session.pending_cancellation = False
            return "error"  # Will show cancellation message
        elif (session and hasattr(session, 'pending_cancellation') and session.pending_cancellation and 
              user_input in ["no", "n", "keep"]):
            # User wants to keep order
            session.pending_cancellation = False
            return "validate"  # Continue with current order
            if (parsed_order.pizza == "EDIT_CART" and parsed_order.size == "CHANGE_QUANTITY"):
                # Change quantity of existing cart item
                if session.cart.items:
                    session.cart.items[0].quantity = parsed_order.quantity
                    session.cart.items[0].total_price = round(session.cart.items[0].base_price * 
                                                       session.cart.items[0].size_multiplier * 
                                                       parsed_order.quantity)
                    session.cart.recalculate()
                return "validate"  # Re-validate and show updated confirmation
            elif (parsed_order.pizza == "EDIT_CART" and parsed_order.size == "REMOVE_ITEM"):
                # Remove item from cart
                session.cart.clear()
                session.confirmation_pending = False
                session.current_order_state = OrderState.CANCELLED
                return "error"  # Show cancellation message
            elif (parsed_order.pizza and parsed_order.pizza != "EDIT_CART" and 
                  parsed_order.size and parsed_order.quantity):
                # Add new item to cart
                return "validate"
        
        # Check if this is a confirmation response (user said "yes" to confirm order)
        if (session and session.confirmation_pending and 
            user_input in ["yes", "y", "confirm", "ok", "proceed", "place"]):
            
            # User confirmed the order, go directly to place order
            session.confirmation_pending = False
            return "place_order"
        elif (session and session.confirmation_pending and 
              user_input in ["no", "n", "cancel", "abort"]):
            # User cancelled the order - clear cart and show cancellation message
            session.cart.clear()
            session.confirmation_pending = False
            session.current_order_state = OrderState.CANCELLED
            # Set a specific cancellation message
            state["user_response"] = "Order cancelled. Would you like to start a new order?"
            state["current_node"] = "show_clarification"
            return "clarify"
            
        # If order has missing information and clarification is available, show clarification
        if parsed_order and parsed_order.missing_info and len(parsed_order.missing_info) > 0:
            if parsed_order.clarification_needed:
                return "clarify"  # Go to clarification node
            else:
                return "error"  # No clarification available, genuine error
            
        # Only proceed if we have complete order information OR multi-order
        if (parsed_order and parsed_order.pizza == "MULTI_ORDER"):
            return "validate"  # Always validate multi-orders
        elif parsed_order and parsed_order.pizza and parsed_order.size and parsed_order.quantity:
            return "validate"
            
        return "error"
    
    def _should_place_order(self, state: OrderingState) -> str:
        """Determine if order should be placed based on user confirmation."""
        if state.get("error_context"):
            return "error"
        
        # Check if user confirmed the order
        user_input = state.get("user_input", "").lower().strip()
        session_id = state.get("session_id")
        session = self.session_manager.get_session(session_id) if session_id else None
        
        if session and session.confirmation_pending:
            if user_input in ["yes", "y", "confirm", "ok", "proceed"]:
                session.confirmation_pending = False
                return "place"
            elif user_input in ["no", "n", "cancel", "abort"]:
                session.cart.clear()
                session.current_order_state = OrderState.CANCELLED
                return "error"
        
        return "error"
    
    def _should_confirm(self, state: OrderingState) -> str:
        """Determine if order should be confirmed."""
        if state.get("error_context"):
            return "error"
        if state.get("order_confirmation"):
            return "confirm"
        return "error"
    
    async def _get_menu_cached(self) -> Optional[List[Dict[str, Any]]]:
        """Get menu with caching."""
        now = datetime.now()
        
        # Check cache validity (5 minutes)
        if (self._menu_cache and self._menu_cache_time and 
            (now - self._menu_cache_time).seconds < 300):
            return self._menu_cache
        
        # Fetch fresh menu
        try:
            mcp_response = await self.mcp_client.get_menu()
            if mcp_response.success and mcp_response.data:
                # MCP response data is already a list of menu items
                if isinstance(mcp_response.data, list):
                    self._menu_cache = mcp_response.data
                    self._menu_cache_time = now
                    return self._menu_cache
        except Exception as e:
            self.logger.error(f"Failed to fetch menu: {e}")
        
        return None
    
    async def cleanup(self):
        """Cleanup resources."""
        await self.mcp_client.disconnect()
    
    async def _send_email_to_scheduling_agent_direct(self, session: SessionState, customer_email: str):
        """Send email to scheduling agent via A2A message"""
        try:
            from agents.communication import A2AMessage, A2AMessageType
            
            # Create A2A message for email processing
            message = A2AMessage(
                type=A2AMessageType.STATUS_UPDATE,
                from_agent=self.agent_id,
                to_agent="scheduling_agent",
                payload={
                    "action": "email_collected",
                    "customer_email": customer_email,
                    "order_id": session.get_recent_order_id() if hasattr(session, 'get_recent_order_id') else "unknown"
                },
                correlation_id=self.session_id
            )
            
            # Send via HTTP to chat server
            import httpx
            async with httpx.AsyncClient() as client:
                await client.post(
                    "http://localhost:8001/api/a2a-message",
                    json=message.dict(),
                    timeout=5.0
                )
                
            self.logger.info(f"Email sent to scheduling agent via A2A: {customer_email}")
            
        except Exception as e:
            self.logger.error(f"Failed to send email to scheduling agent: {e}")
    
    async def _update_order_customer_email(self, order_id: str, customer_email: str):
        """Update order with customer email via backend API"""
        try:
            import httpx
            
            # Use backend API endpoint instead of direct database access
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"http://localhost:8000/orders/{order_id}/email",
                    json={"customer_email": customer_email},
                    timeout=5.0
                )
                
                if response.status_code == 200:
                    self.logger.info(f"Updated order {order_id} with customer email: {customer_email}")
                else:
                    self.logger.error(f"Failed to update order email: {response.status_code}")
                    
        except Exception as e:
            self.logger.error(f"Failed to update order with customer email: {e}")
    
    # Tier 2 Enhancement Methods
    
    def _is_cancellation_request(self, user_input: str) -> bool:
        """Check if user is requesting to cancel order"""
        cancel_keywords = ["cancel", "abort", "stop", "nevermind", "forget it"]
        return any(keyword in user_input for keyword in cancel_keywords)
    
    async def _handle_cancellation_request(self, state: OrderingState, session: SessionState) -> OrderingState:
        """Handle order cancellation request with context-aware responses."""
        current_state = session.current_order_state
        
        if current_state == OrderState.PENDING_CONFIRMATION:
            # Cancel pending order
            session.cart.clear()
            session.current_order_state = OrderState.DRAFT
            state["user_response"] = "✅ Order cancelled. Your cart is now empty. Would you like to start a new order?"
        elif current_state == OrderState.RESTAURANT_PENDING:
            state["user_response"] = "Your order is already with the restaurant and cannot be cancelled. Please contact support if needed."
        else:
            # No active order to cancel
            state["user_response"] = "You don't have any active orders to cancel. Would you like to place a new order?"
        
        state["current_node"] = "show_clarification"
        return state
    
    async def _handle_confirmation_request(self, state: OrderingState, session: SessionState) -> OrderingState:
        """Handle order confirmation when user says yes."""
        if session.current_order_state == OrderState.PENDING_CONFIRMATION and session.cart.items:
            # Proceed to place order
            state["current_node"] = "place_order"
            return state
        else:
            state["user_response"] = "There's no order to confirm. Would you like to place a new order?"
            state["current_node"] = "show_clarification"
            return state
    
    async def _handle_add_to_cart_request(self, state: OrderingState, session: SessionState) -> OrderingState:
        """Handle request to add more items to cart."""
        menu = await self._get_menu_cached()
        menu_items = [item["name"] for item in menu] if menu else []
        
        # Show popular options for quick selection
        popular_items = menu_items[:5] if menu_items else []
        popular_list = ", ".join(popular_items)
        
        state["user_response"] = f"What pizza would you like to add to your order?\n\nPopular choices: {popular_list}\n\nOr say 'menu' to see all options."
        state["current_node"] = "show_clarification"
        return state
    
    async def _handle_remove_from_cart_request(self, state: OrderingState, session: SessionState) -> OrderingState:
        """Handle request to remove items from cart."""
        if not session.cart.items:
            state["user_response"] = "Your cart is empty. Would you like to add some pizzas?"
            state["current_node"] = "show_clarification"
            return state
        
        if len(session.cart.items) == 1:
            item = session.cart.items[0]
            state["user_response"] = f"Remove {item.pizza} ({item.size}) from your cart? Say 'yes' to remove it or 'no' to keep it."
            state["current_node"] = "show_clarification"
            return state
        else:
            # Multiple items - show numbered list
            cart_list = ""
            for i, item in enumerate(session.cart.items, 1):
                cart_list += f"{i}. {item.pizza} ({item.size}) x{item.quantity} - Rs.{item.total_price}\n"
            
            state["user_response"] = f"Which item would you like to remove?\n\n{cart_list}\nSay the number (e.g., '1') or the pizza name."
            state["current_node"] = "show_clarification"
            return state
    
    async def _handle_show_cart_request(self, state: OrderingState, session: SessionState) -> OrderingState:
        """Handle request to show current cart."""
        if not session.cart.items:
            state["user_response"] = "Your cart is empty. Would you like to add some pizzas?"
        else:
            # Format cart summary
            cart_summary = "🛒 Your Current Order:\n\n"
            for i, item in enumerate(session.cart.items, 1):
                cart_summary += f"{i}. {item.pizza} ({item.size}) x{item.quantity} - Rs.{item.total_price}\n"
            
            cart_summary += f"\nSubtotal: Rs.{session.cart.subtotal}"
            if session.cart.delivery_fee > 0:
                cart_summary += f"\nDelivery Fee: Rs.{session.cart.delivery_fee}"
            else:
                cart_summary += f"\nDelivery: FREE"
            cart_summary += f"\nTotal: Rs.{session.cart.total}"
            cart_summary += f"\n\nSay 'yes' to confirm, 'add more' to add items, or 'remove' to remove items."
            
            state["user_response"] = cart_summary
        
        state["current_node"] = "show_clarification"
        return state
    
    async def _handle_show_menu_request(self, state: OrderingState, session: SessionState) -> OrderingState:
        """Handle request to show menu."""
        menu = await self._get_menu_cached()
        if not menu:
            state["user_response"] = "Sorry, I couldn't load the menu right now. Please try again."
            state["current_node"] = "handle_error"
            return state
        
        # Show categorized menu
        veg_items = []
        non_veg_items = []
        
        for item in menu:
            name_price = f"{item['name']} - Rs.{item['price']}"
            # Simple categorization based on common patterns
            if any(veg_word in item['name'].lower() for veg_word in ['paneer', 'corn', 'aloo', 'palak', 'rajma', 'chole']):
                veg_items.append(name_price)
            else:
                non_veg_items.append(name_price)
        
        menu_text = "🍕 Our Pizza Menu:\n\n"
        if veg_items:
            menu_text += "🥬 Vegetarian:\n" + "\n".join(veg_items[:8]) + "\n\n"
        if non_veg_items:
            menu_text += "🍗 Non-Vegetarian:\n" + "\n".join(non_veg_items[:8]) + "\n\n"
        
        menu_text += "Just tell me which pizza you'd like!"
        
        state["user_response"] = menu_text
        state["current_node"] = "show_clarification"
        return state
    
    async def _handle_help_request(self, state: OrderingState, session: SessionState) -> OrderingState:
        """Handle help request with context-aware guidance."""
        current_state = session.current_order_state if session else OrderState.DRAFT
        
        if current_state == OrderState.PENDING_CONFIRMATION:
            help_text = """🤖 I can help you with your pending order:
            
• Say 'yes' or 'confirm' to place your order
• Say 'no' or 'cancel' to start over
• Say 'add more' to add another pizza
• Say 'remove' to remove items
• Say 'cart' to see your current order"""
        else:
            help_text = """🤖 I'm your pizza ordering assistant! I can help you:
            
• Order pizzas (just say what you want!)
• Show the menu ('menu' or 'what do you have')
• Check your cart ('cart' or 'my order')
• Cancel orders ('cancel' or 'nevermind')

Just tell me what pizza you'd like to order!"""
        
        state["user_response"] = help_text
        state["current_node"] = "show_clarification"
        return state
    
    def _create_context_aware_prompt(self, menu_items: List[str], session: Optional[SessionState]) -> str:
        """Create context-aware prompt with conversation history"""
        
        base_prompt = f"""You are a professional pizza ordering assistant. 

CRITICAL RULE: You MUST respond with ONLY valid JSON. No text before or after the JSON. No markdown formatting. No explanations.

MULTI-PIZZA DETECTION RULES:
- If input contains comma (,) between pizza names → MULTI_ORDER
- If input contains "and" between pizza names → MULTI_ORDER  
- If input contains "plus" between pizza names → MULTI_ORDER
- If input mentions 2+ different pizza names → MULTI_ORDER
- Examples: "Margherita, Pepperoni", "Margherita and Pepperoni", "Margherita plus Pepperoni"

SIZE MAPPING RULES:
- "larger", "big", "biggest" → "large"
- "smaller", "tiny" → "small"  
- "regular", "normal", "standard" → "medium"
- Always use: "small", "medium", "large" in output

MENU CONTEXT:
Available pizzas: {', '.join(menu_items)}
Available sizes: small, medium, large
Default quantity: 1 (if not specified)

INTELLIGENT RESPONSE RULES:
1. ALWAYS respond with valid JSON matching the schema below
2. For pizza orders: Set pizza name, size, quantity, confidence 1.0
3. For menu requests: First show popular items + option for full menu
4. For "full menu" requests: Show complete database menu
5. For size clarification: Mention the three available sizes (small, medium, large)
6. EMAIL COLLECTION: Before finalizing order, ask for customer email for order updates
7. CONTEXT AWARENESS: Use conversation history to understand short responses
8. Be conversational and helpful in clarification_needed field using real menu data
9. MULTI-PIZZA PROCESSING: If user mentions multiple pizzas (comma OR "and"), ALWAYS use MULTI_ORDER format. Look for keywords: comma, "and", "plus", multiple pizza names in one message.

CONTEXT-AWARE EXAMPLES (respond with EXACTLY this format):

Input: "Margherita"
Output: {{"pizza": "Margherita", "size": "medium", "quantity": 1, "confidence": 1.0, "missing_info": [], "clarification_needed": null, "special_instructions": null}}

Input: "Large pepperoni pizza"
Output: {{"pizza": "Pepperoni", "size": "large", "quantity": 1, "confidence": 1.0, "missing_info": [], "clarification_needed": null, "special_instructions": null}}

Input: "larger Margherita" or "big Margherita"
Output: {{"pizza": "Margherita", "size": "large", "quantity": 1, "confidence": 1.0, "missing_info": [], "clarification_needed": null, "special_instructions": null}}

Input: "small" (when previous message asked "Which size would you prefer?")
Output: {{"pizza": "Pepperoni", "size": "small", "quantity": 1, "confidence": 1.0, "missing_info": [], "clarification_needed": null, "special_instructions": null}}

Input: "medium" (when previous message asked about size)
Output: {{"pizza": "Margherita", "size": "medium", "quantity": 1, "confidence": 1.0, "missing_info": [], "clarification_needed": null, "special_instructions": null}}

Input: "large" (when previous message asked about size)
Output: {{"pizza": "Margherita", "size": "large", "quantity": 1, "confidence": 1.0, "missing_info": [], "clarification_needed": null, "special_instructions": null}}

Input: "show menu" or "menu" or "what do you have"
Output: {{"pizza": null, "size": null, "quantity": null, "confidence": 0.3, "missing_info": ["pizza"], "clarification_needed": "Here are our popular pizzas: Margherita, Pepperoni, Hawaiian, BBQ Chicken. Would you like to try one of these or see our full menu?", "special_instructions": null}}

Input: "full menu" or "complete menu" or "all pizzas" or "see full menu"
Output: {{"pizza": null, "size": null, "quantity": null, "confidence": 0.3, "missing_info": ["pizza"], "clarification_needed": "Here's our complete menu: Margherita, Pepperoni, Veggie, BBQ Chicken, Hawaiian, Meat Lovers, White Pizza, Buffalo Chicken, Mediterranean, Mushroom Truffle, Spicy Italian, Four Cheese, Prosciutto Arugula, Taco Pizza, Breakfast Pizza, Vegan Delight, Seafood Supreme, Pesto Chicken, Mexican Fiesta, Classic Supreme. Which one would you like?", "special_instructions": null}}

Input: "Margherita pizza" (no size specified)
Output: {{"pizza": "Margherita", "size": null, "quantity": 1, "confidence": 0.8, "missing_info": ["size"], "clarification_needed": "Great choice! We have Margherita in three sizes: small, medium, and large. Which size would you prefer?", "special_instructions": null}}

Input: "I want Margherita" (no size specified)
Output: {{"pizza": "Margherita", "size": null, "quantity": 1, "confidence": 0.8, "missing_info": ["size"], "clarification_needed": "Perfect! Margherita is available in small, medium, and large. Which size would you like?", "special_instructions": null}}

Input: "Pepperoni" (no size specified)
Output: {{"pizza": "Pepperoni", "size": null, "quantity": 1, "confidence": 0.8, "missing_info": ["size"], "clarification_needed": "Excellent choice! Pepperoni comes in small, medium, and large. What size would you prefer?", "special_instructions": null}}

Input: "I want pizza" or "suggest something"
Output: {{"pizza": null, "size": null, "quantity": null, "confidence": 0.3, "missing_info": ["pizza"], "clarification_needed": "I'd recommend our popular choices: Margherita (classic), Pepperoni (favorite), or BBQ Chicken (delicious). Which sounds good, or would you like to see our full menu?", "special_instructions": null}}

Input: "yes" (when previous assistant message was asking "Which sounds good, or would you like to see our full menu?")
Output: {{"pizza": null, "size": null, "quantity": null, "confidence": 0.3, "missing_info": ["pizza"], "clarification_needed": "Great! Which pizza would you like to try? We have Margherita (classic), Pepperoni (favorite), or BBQ Chicken (delicious). Just let me know which one!", "special_instructions": null}}

Input: "Margherita, Pepperoni" (multiple pizzas - ALWAYS detect comma or "and")
Output: {{"pizza": "MULTI_ORDER", "size": "MULTI_ORDER", "quantity": 2, "confidence": 1.0, "missing_info": [], "clarification_needed": null, "special_instructions": "PIZZAS:Margherita:medium:1,Pepperoni:medium:1"}}

Input: "Margherita and Pepperoni" (multiple pizzas - ALWAYS detect comma or "and")
Output: {{"pizza": "MULTI_ORDER", "size": "MULTI_ORDER", "quantity": 2, "confidence": 1.0, "missing_info": [], "clarification_needed": null, "special_instructions": "PIZZAS:Margherita:medium:1,Pepperoni:medium:1"}}

Input: "large Margherita, small Pepperoni" (multiple pizzas with sizes)
Output: {{"pizza": "MULTI_ORDER", "size": "MULTI_ORDER", "quantity": 2, "confidence": 1.0, "missing_info": [], "clarification_needed": null, "special_instructions": "PIZZAS:Margherita:large:1,Pepperoni:small:1"}}

Input: "2 Margherita and 1 Pepperoni" (multiple pizzas with quantities)
Output: {{"pizza": "MULTI_ORDER", "size": "MULTI_ORDER", "quantity": 3, "confidence": 1.0, "missing_info": [], "clarification_needed": null, "special_instructions": "PIZZAS:Margherita:medium:2,Pepperoni:medium:1"}}

Input: "Margherita and Pepperoni small size one each" (multiple pizzas with size)
Output: {{"pizza": "MULTI_ORDER", "size": "MULTI_ORDER", "quantity": 2, "confidence": 1.0, "missing_info": [], "clarification_needed": null, "special_instructions": "PIZZAS:Margherita:small:1,Pepperoni:small:1"}}

Input: "cancel my order" or "cancel order" or "i want to cancel"
Output: {{"pizza": "CANCEL_REQUEST", "size": "CANCEL_REQUEST", "quantity": 0, "confidence": 1.0, "missing_info": [], "clarification_needed": "Are you sure you want to cancel your current order? Reply 'yes' to cancel or 'no' to keep your order.", "special_instructions": null}}

Input: "edit cart" or "modify order" or "change my order"
Output: {{"pizza": "EDIT_CART", "size": "EDIT_CART", "quantity": 0, "confidence": 1.0, "missing_info": [], "clarification_needed": "What would you like to change in your cart? You can add more pizzas, change quantities, or remove items.", "special_instructions": null}}

Input: "change quantity to 3" (when cart has items and confirmation pending)
Output: {{"pizza": "EDIT_CART", "size": "CHANGE_QUANTITY", "quantity": 3, "confidence": 1.0, "missing_info": [], "clarification_needed": null, "special_instructions": null}}

Input: "make it 2 pizzas" (when cart has items and confirmation pending)  
Output: {{"pizza": "EDIT_CART", "size": "CHANGE_QUANTITY", "quantity": 2, "confidence": 1.0, "missing_info": [], "clarification_needed": null, "special_instructions": null}}

Input: "remove item" or "cancel this item" (when cart has items and confirmation pending)
Output: {{"pizza": "EDIT_CART", "size": "REMOVE_ITEM", "quantity": 0, "confidence": 1.0, "missing_info": [], "clarification_needed": null, "special_instructions": null}}

Input: "add large margherita" (when cart has items and confirmation pending)
Output: {{"pizza": "Margherita", "size": "large", "quantity": 1, "confidence": 1.0, "missing_info": [], "clarification_needed": null, "special_instructions": null}}

CRITICAL CONTEXT RULES:
- ALWAYS check RECENT CONVERSATION above for context
- If user says size words (small/medium/large) and previous message asked about size, extract the pizza name from conversation history
- If user says "full menu" or "complete menu", show ALL pizzas from menu context
- If user says "yes" and previous message was asking "Would you like to try one of these", DO NOT place order - ask which specific pizza
- If user says "yes" and previous message was "Would you like to confirm this order?", then proceed with order
- Use conversation history to understand what the user is responding to

IMPORTANT: Look at the assistant's previous message to understand what the user is responding to.

{self.output_parser.get_format_instructions()}

Remember: Use the actual menu data from MENU CONTEXT above in your responses. Be helpful and conversational."""
        
        # Add conversation context if available
        if session and session.context.conversation_history:
            recent_context = session.context.get_recent_context(3)
            if recent_context:
                context_summary = "RECENT CONVERSATION:\n"
                for msg in recent_context:
                    role = msg.get("role", "unknown")
                    content = msg.get("content", "")[:100]  # Limit length
                    context_summary += f"- {role}: {content}\n"
                base_prompt = context_summary + "\n" + base_prompt
        
        return base_prompt
