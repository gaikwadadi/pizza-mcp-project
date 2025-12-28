"""
Enhanced error handling and recovery system.
Industry best practice: Graceful error recovery with smart alternatives.
"""
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

@dataclass
class ErrorContext:
    """Context for error handling and recovery"""
    error_type: str
    user_input: str
    attempted_action: str
    available_alternatives: List[str] = None
    conversation_context: List[Dict[str, Any]] = None

class SmartErrorHandler:
    """Handles errors with intelligent recovery suggestions"""
    
    def __init__(self, menu_items: List[str]):
        self.menu_items = menu_items
        self.similar_items = self._build_similarity_map()
    
    def handle_error(self, context: ErrorContext) -> str:
        """Handle error with smart recovery suggestions"""
        error_type = context.error_type.lower()
        
        if "not found" in error_type or "unavailable" in error_type:
            return self._handle_item_not_found(context)
        
        if "network" in error_type or "connection" in error_type:
            return self._handle_network_error(context)
        
        if "unclear" in error_type or "ambiguous" in error_type:
            return self._handle_unclear_input(context)
        
        if "out of stock" in error_type:
            return self._handle_out_of_stock(context)
        
        # Default recovery
        return self._handle_generic_error(context)
    
    def _handle_item_not_found(self, context: ErrorContext) -> str:
        """Handle pizza not found with similar suggestions"""
        user_input = context.user_input.lower()
        
        # Find similar items
        suggestions = self._find_similar_items(user_input)
        
        if suggestions:
            if len(suggestions) == 1:
                return f"I couldn't find that exact pizza, but we have {suggestions[0]} which might be what you're looking for. Would you like that instead?"
            else:
                return f"I couldn't find that pizza, but here are some similar options: {', '.join(suggestions[:3])}. Which one interests you?"
        
        return "I couldn't find that pizza on our menu. Would you like to see our available options or try a different name?"
    
    def _handle_network_error(self, context: ErrorContext) -> str:
        """Handle network/connection errors"""
        return "I'm having trouble connecting to our system right now. Let me try that again for you..."
    
    def _handle_unclear_input(self, context: ErrorContext) -> str:
        """Handle unclear or ambiguous input"""
        recent_context = self._get_recent_context(context.conversation_context)
        
        if recent_context:
            return f"I want to make sure I understand correctly. Did you mean {recent_context} or something else?"
        
        return "I'm not quite sure what you meant. Could you be more specific? For example, you could say 'I want a large Margherita pizza'."
    
    def _handle_out_of_stock(self, context: ErrorContext) -> str:
        """Handle out of stock items with alternatives"""
        if context.available_alternatives:
            return f"Sorry, that item is currently out of stock. Here are some great alternatives: {', '.join(context.available_alternatives[:3])}. Which one would you like?"
        
        return "Sorry, that item is currently unavailable. Would you like to see our available menu options?"
    
    def _handle_generic_error(self, context: ErrorContext) -> str:
        """Handle generic errors with helpful recovery"""
        return "I encountered an issue processing your request. Let's start fresh - what would you like to order today?"
    
    def _find_similar_items(self, user_input: str) -> List[str]:
        """Find similar menu items based on user input"""
        suggestions = []
        
        # Simple similarity matching
        for item in self.menu_items:
            item_lower = item.lower()
            if any(word in item_lower for word in user_input.split() if len(word) > 2):
                suggestions.append(item)
        
        # Add popular alternatives if no matches
        if not suggestions:
            if "meat" in user_input or "chicken" in user_input:
                suggestions = ["BBQ Chicken", "Buffalo Chicken", "Meat Lovers"]
            elif "veg" in user_input or "vegetable" in user_input:
                suggestions = ["Veggie", "Mediterranean", "Vegan Delight"]
            elif "cheese" in user_input:
                suggestions = ["Four Cheese", "Margherita", "White Pizza"]
        
        return suggestions[:3]  # Limit to 3 suggestions
    
    def _build_similarity_map(self) -> Dict[str, List[str]]:
        """Build similarity map for menu items"""
        # Simple similarity mapping - could be enhanced with ML
        return {
            "margherita": ["Margherita", "White Pizza", "Four Cheese"],
            "pepperoni": ["Pepperoni", "Spicy Italian", "Meat Lovers"],
            "veggie": ["Veggie", "Mediterranean", "Vegan Delight"],
            "chicken": ["BBQ Chicken", "Buffalo Chicken", "Pesto Chicken"]
        }
    
    def _get_recent_context(self, conversation_context: List[Dict[str, Any]]) -> Optional[str]:
        """Extract recent context for clarification"""
        if not conversation_context:
            return None
        
        # Look for pizza names in recent messages
        for msg in reversed(conversation_context[-3:]):
            content = msg.get("content", "").lower()
            for item in self.menu_items:
                if item.lower() in content:
                    return item
        
        return None
