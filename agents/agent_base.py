"""
Base class for all AI agents providing shared infrastructure and utilities.
"""
import os
import logging
import uuid
from typing import Dict, Any, Optional
from datetime import datetime
from abc import ABC, abstractmethod

from langchain_groq import ChatGroq
from dotenv import load_dotenv
from utils.timezone_utils import tz_manager

# Load environment variables
load_dotenv()

class AgentBase(ABC):
    """Base class for all AI agents with shared infrastructure."""
    
    def __init__(
        self, 
        agent_id: str,
        agent_name: str = None,
        model_name: str = None,
        temperature: float = None
    ):
        """Initialize base agent with LLM and infrastructure."""
        self.agent_id = agent_id
        self.agent_name = agent_name or os.getenv("AGENT_NAME") or agent_id.replace('_', ' ').title()
        self.session_id = self._generate_session_id()
        
        # Get configuration from environment - NO FALLBACKS
        self.model_name = model_name or os.getenv("GROQ_MODEL_ID")
        self.temperature = temperature if temperature is not None else float(os.getenv("AGENT_TEMPERATURE"))
        
        # Validate required configuration
        if not self.model_name:
            raise ValueError("GROQ_MODEL_ID environment variable is required")
        if self.temperature is None:
            raise ValueError("AGENT_TEMPERATURE environment variable is required")
        
        # Setup logging
        self.logger = self._setup_logging()
        
        # Initialize LLM
        self.llm = self._setup_llm(self.model_name, self.temperature)
        
        # Agent configuration
        self.config = {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "version": "1.0.0",
            "session_id": self.session_id
        }
        
        self.logger.info(f"Agent {self.agent_name} initialized with session {self.session_id}")
    
    def _generate_session_id(self) -> str:
        """Generate unique session identifier with IST timestamp."""
        timestamp = tz_manager.now_local().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        return f"session_{timestamp}_{unique_id}"
    
    def _setup_logging(self) -> logging.Logger:
        """Setup structured logging for the agent."""
        logger = logging.getLogger(f"agent.{self.agent_id}")
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                f'%(asctime)s - {self.agent_id} - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def _setup_llm(self, model_name: str, temperature: float) -> ChatGroq:
        """Initialize Groq LLM with configuration."""
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY environment variable is required")
        
        try:
            llm = ChatGroq(
                model=model_name,
                temperature=temperature,
                groq_api_key=api_key
            )
            self.logger.info(f"LLM initialized: {model_name} (temp={temperature})")
            return llm
        except Exception as e:
            self.logger.error(f"Failed to initialize LLM: {e}")
            raise
    
    def log_interaction(self, interaction_type: str, data: Dict[str, Any]) -> None:
        """Log agent interactions with structured data."""
        log_data = {
            "session_id": self.session_id,
            "agent_id": self.agent_id,
            "interaction_type": interaction_type,
            "timestamp": datetime.now().isoformat(),
            **data
        }
        self.logger.info(f"Interaction: {interaction_type}", extra=log_data)
    
    def handle_error(self, error: Exception, context: str = "") -> Dict[str, Any]:
        """Handle errors with logging and structured response."""
        error_id = str(uuid.uuid4())[:8]
        error_data = {
            "error_id": error_id,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context,
            "session_id": self.session_id
        }
        
        self.logger.error(f"Error {error_id}: {error}", extra=error_data)
        
        return {
            "success": False,
            "error": {
                "id": error_id,
                "type": type(error).__name__,
                "message": "An error occurred while processing your request.",
                "context": context
            }
        }
    
    def get_agent_info(self) -> Dict[str, Any]:
        """Get agent information and status."""
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "session_id": self.session_id,
            "version": self.config["version"],
            "status": "active",
            "capabilities": self.get_capabilities()
        }
    
    @abstractmethod
    def get_capabilities(self) -> list:
        """Return list of agent capabilities."""
        pass
    
    @abstractmethod
    def process_request(self, user_input: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process user request - to be implemented by subclasses."""
        pass
