"""
Intelligent clarification system for context-aware follow-up questions.
Industry best practice: Smart question generation based on conversation context.
"""
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

@dataclass
class ClarificationContext:
    """Context for generating intelligent clarifications"""
    user_input: str
    conversation_history: List[Dict[str, Any]]
    mentioned_items: List[str]
    menu_items: List[str]
    last_intent: Optional[str] = None

class IntelligentClarifier:
    """Generates context-aware clarification questions"""
    
    def __init__(self):
        self.popular_items = ["Margherita", "Pepperoni", "BBQ Chicken", "Veggie"]
        self.size_keywords = ["small", "medium", "large"]
        self.quantity_keywords = ["one", "two", "three", "1", "2", "3"]
    
    def generate_clarification(self, context: ClarificationContext) -> str:
        """Generate intelligent clarification based on context"""
        user_input = context.user_input.lower()
        
        # Check what information is missing
        missing_pizza = not any(item.lower() in user_input for item in context.menu_items)
        missing_size = not any(size in user_input for size in self.size_keywords)
        missing_quantity = not any(qty in user_input for qty in self.quantity_keywords)
        
        # Context-aware clarifications
        if "pizza" in user_input and missing_pizza:
            return self._suggest_pizza_options(context)
        
        if missing_pizza and missing_size:
            return self._ask_for_complete_order(context)
        
        if not missing_pizza and missing_size:
            pizza_name = self._extract_pizza_name(user_input, context.menu_items)
            return f"What size {pizza_name} would you like? We have small, medium, and large available."
        
        if "size" in user_input or any(size in user_input for size in self.size_keywords):
            return self._clarify_size_context(context)
        
        # Default intelligent clarification
        return self._generate_smart_default(context)
    
    def _suggest_pizza_options(self, context: ClarificationContext) -> str:
        """Suggest pizza options based on popularity and context"""
        recent_mentions = self._get_recent_pizza_mentions(context.conversation_history)
        
        if recent_mentions:
            return f"Which pizza would you like? You mentioned {recent_mentions[0]} earlier, or would you prefer something else from our menu?"
        
        return f"Which pizza would you like? Our popular choices are {', '.join(self.popular_items[:3])}, or would you like to see the full menu?"
    
    def _ask_for_complete_order(self, context: ClarificationContext) -> str:
        """Ask for complete order information"""
        return f"I'd be happy to help you order! Which pizza would you like and what size? Our popular options are {', '.join(self.popular_items[:3])} in small, medium, or large."
    
    def _clarify_size_context(self, context: ClarificationContext) -> str:
        """Clarify size in context of conversation"""
        recent_pizzas = self._get_recent_pizza_mentions(context.conversation_history)
        
        if recent_pizzas:
            pizza = recent_pizzas[0]
            size = self._extract_size(context.user_input)
            if size:
                return f"Perfect! So you'd like a {size} {pizza} pizza. Is that correct?"
        
        return "What size would you like? We have small, medium, and large available."
    
    def _generate_smart_default(self, context: ClarificationContext) -> str:
        """Generate smart default clarification"""
        if len(context.conversation_history) > 2:
            return "I want to make sure I get your order right. Could you tell me which pizza you'd like and what size?"
        
        return f"What can I get for you today? Our menu includes {', '.join(self.popular_items)} and many more options."
    
    def _extract_pizza_name(self, user_input: str, menu_items: List[str]) -> Optional[str]:
        """Extract pizza name from user input"""
        user_lower = user_input.lower()
        for item in menu_items:
            if item.lower() in user_lower:
                return item
        return None
    
    def _extract_size(self, user_input: str) -> Optional[str]:
        """Extract size from user input"""
        user_lower = user_input.lower()
        for size in self.size_keywords:
            if size in user_lower:
                return size
        return None
    
    def _get_recent_pizza_mentions(self, history: List[Dict[str, Any]]) -> List[str]:
        """Get recently mentioned pizzas from conversation history"""
        mentioned = []
        for msg in reversed(history[-5:]):  # Last 5 messages
            content = msg.get("content", "").lower()
            # Simple extraction - could be enhanced
            for pizza in self.popular_items:
                if pizza.lower() in content and pizza not in mentioned:
                    mentioned.append(pizza)
        return mentioned
