"""
Session context management for conversational state tracking.
Industry best practice: Maintain conversation context and user state.
"""
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

class OrderState(Enum):
    """Order lifecycle states"""
    DRAFT = "draft"
    PENDING_CONFIRMATION = "pending_confirmation"
    SUBMITTED = "submitted"
    RESTAURANT_PENDING = "restaurant_pending"
    ACCEPTED = "accepted"
    PREPARING = "preparing"
    READY = "ready"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    CONFIRMED = "confirmed"  # Legacy state
    CANCELLED = "cancelled"

@dataclass
class CartItem:
    """Individual cart item with all details"""
    pizza: str
    size: str
    quantity: int
    base_price: float
    size_multiplier: float
    total_price: float
    special_instructions: Optional[str] = None

@dataclass
class OrderHistory:
    """Track order history and status"""
    order_id: str
    items: List['CartItem']  # Use string reference to avoid forward reference issue
    total: float
    status: OrderState
    created_at: datetime
    confirmed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    
    def can_cancel(self) -> bool:
        """Check if order can be cancelled (within 1 minute of confirmation)"""
        if self.status != OrderState.CONFIRMED or not self.confirmed_at:
            return False
        
        time_since_confirmation = datetime.now() - self.confirmed_at
        return time_since_confirmation.total_seconds() <= 60  # 1 minute grace period
    
    def get_status_message(self) -> str:
        """Get user-friendly status message"""
        status_messages = {
            OrderState.DRAFT: "Order being prepared",
            OrderState.PENDING_CONFIRMATION: "Waiting for your confirmation",
            OrderState.CONFIRMED: "Order confirmed and being prepared",
            OrderState.PREPARING: "Your pizza is being prepared",
            OrderState.OUT_FOR_DELIVERY: "Out for delivery",
            OrderState.DELIVERED: "Delivered",
            OrderState.CANCELLED: "Cancelled"
        }
        return status_messages.get(self.status, "Unknown status")

@dataclass
class Cart:
    """Shopping cart with items and totals"""
    items: List[CartItem] = field(default_factory=list)
    subtotal: float = 0.0
    delivery_fee: float = 0.0
    total: float = 0.0
    estimated_prep_time: int = 20  # minutes
    
    def add_item(self, item: CartItem):
        """Add item to cart and recalculate totals"""
        self.items.append(item)
        self.recalculate()
    
    def remove_item(self, index: int):
        """Remove item by index and recalculate"""
        if 0 <= index < len(self.items):
            self.items.pop(index)
            self.recalculate()
    
    def clear(self):
        """Clear all items"""
        self.items.clear()
        self.recalculate()
    
    def recalculate(self):
        """Recalculate cart totals"""
        self.subtotal = sum(item.total_price for item in self.items)
        self.delivery_fee = 50.0 if self.subtotal < 500 else 0.0  # Free delivery over ₹500
        self.total = self.subtotal + self.delivery_fee
        # Estimate prep time: 20 min base + 5 min per additional item
        self.estimated_prep_time = 20 + max(0, (len(self.items) - 1) * 5)

@dataclass
class ConversationContext:
    """Conversation state and context tracking"""
    session_id: str
    user_id: Optional[str] = None
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)
    current_intent: Optional[str] = None
    last_clarification: Optional[str] = None
    mentioned_items: List[str] = field(default_factory=list)
    preferences: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def add_message(self, role: str, content: str, metadata: Optional[Dict] = None):
        """Add message to conversation history"""
        self.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        })
        self.updated_at = datetime.now()
    
    def get_recent_context(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get recent conversation context"""
        return self.conversation_history[-limit:]
    
    def extract_mentioned_items(self, text: str, menu_items: List[str]):
        """Extract and remember mentioned menu items"""
        text_lower = text.lower()
        for item in menu_items:
            if item.lower() in text_lower and item not in self.mentioned_items:
                self.mentioned_items.append(item)

@dataclass
class SessionState:
    """Complete session state including cart and context"""
    session_id: str
    context: ConversationContext
    cart: Cart = field(default_factory=Cart)
    current_order_state: OrderState = OrderState.DRAFT
    order_id: Optional[str] = None
    order_history: List[OrderHistory] = field(default_factory=list)
    confirmation_pending: bool = False
    pending_cancellation: bool = False  # For cancellation confirmation
    pending_multi_pizza: Optional[dict] = None  # For multi-pizza requests
    auto_process_next: bool = False  # Auto-process next pizza in multi-pizza orders
    add_pending_to_cart: bool = False  # Flag to add pending pizza to cart
    # Removed: pending_email_collection and customer_email (not stored)
    last_activity: datetime = field(default_factory=datetime.now)
    
    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = datetime.now()
        self.context.updated_at = datetime.now()
    
    def add_to_history(self, order: OrderHistory):
        """Add order to history"""
        self.order_history.append(order)
    
    def get_recent_order(self) -> Optional[OrderHistory]:
        """Get most recent order"""
        return self.order_history[-1] if self.order_history else None
    
    def can_cancel_recent_order(self) -> bool:
        """Check if recent order can be cancelled"""
        recent = self.get_recent_order()
        return recent.can_cancel() if recent else False

class SessionManager:
    """Manages user sessions and context"""
    
    def __init__(self):
        self.sessions: Dict[str, SessionState] = {}
        self.session_timeout = 1800  # 30 minutes
    
    def get_or_create_session(self, session_id: str, user_id: Optional[str] = None) -> SessionState:
        """Get existing session or create new one"""
        if session_id not in self.sessions:
            context = ConversationContext(session_id=session_id, user_id=user_id)
            self.sessions[session_id] = SessionState(
                session_id=session_id,
                context=context
            )
        
        session = self.sessions[session_id]
        session.update_activity()
        return session
    
    def cleanup_expired_sessions(self):
        """Remove expired sessions"""
        now = datetime.now()
        expired_sessions = [
            sid for sid, session in self.sessions.items()
            if (now - session.last_activity).seconds > self.session_timeout
        ]
        for sid in expired_sessions:
            del self.sessions[sid]
    
    def get_session(self, session_id: str) -> Optional[SessionState]:
        """Get session if exists"""
        return self.sessions.get(session_id)
    
    def clear_session(self, session_id: str) -> bool:
        """Clear a specific session"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False
