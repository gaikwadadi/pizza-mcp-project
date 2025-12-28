"""
FastAPI WebSocket server for pizza chat interface.
Integrates with existing ordering and scheduling agents.
"""
import asyncio
import json
import sys
import subprocess
import signal
import os
import webbrowser
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.timezone_utils import tz_manager
from agents.ordering_agent import PizzaOrderingAgent
from agents.scheduling_agent import PizzaSchedulingAgent
from utils.timezone_utils import tz_manager

app = FastAPI(title="Pizza Chat Interface", version="1.0.0")

# Serve static files
app.mount("/static", StaticFiles(directory="chat_interface/static"), name="static")

class ChatManager:
    """Manages chat sessions and agent interactions."""
    
    def __init__(self):
        self.ordering_agent = None
        self.scheduling_agent = None
        self.active_connections: Dict[str, WebSocket] = {}
        self.pending_orders: Dict[str, Dict] = {}  # Track orders waiting for business approval
        self.mcp_server_process = None
        self.backend_process = None
        
    async def start_backend_server(self):
        """Start the backend server if not running."""
        try:
            # Check if backend is already running
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get("http://localhost:8000/health", timeout=2.0)
                if response.status_code == 200:
                    print("✅ Backend server already running")
                    return True
        except:
            pass
            
        # Start backend server
        print("🚀 Starting backend server...")
        backend_path = project_root / "backend" / "main.py"
        
        self.backend_process = subprocess.Popen([
            sys.executable, "-m", "uvicorn", "backend.main:app", 
            "--host", "0.0.0.0", "--port", "8000"
        ], cwd=project_root, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Wait for backend to start
        await asyncio.sleep(3)
        
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get("http://localhost:8000/health", timeout=5.0)
                if response.status_code == 200:
                    print("✅ Backend server started successfully")
                    return True
        except:
            print("❌ Backend server failed to start")
            return False
            
    async def start_mcp_server(self):
        """Start the HTTP-based MCP server."""
        try:
            # Check if MCP server is already running
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get("http://localhost:3000/health", timeout=2.0)
                if response.status_code == 200:
                    print("✅ MCP server already running")
                    return True
        except:
            pass
            
        print("🚀 Starting HTTP MCP server...")
        mcp_server_path = project_root / "generated" / "pizza_mcp_server_http.py"
        
        # Start HTTP MCP server process
        self.mcp_server_process = subprocess.Popen([
            sys.executable, str(mcp_server_path)
        ], cwd=project_root, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Wait for MCP server to start
        await asyncio.sleep(3)
        
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get("http://localhost:3000/health", timeout=5.0)
                if response.status_code == 200:
                    print("✅ HTTP MCP server started successfully")
                    return True
        except:
            print("❌ HTTP MCP server failed to start")
            return False
        
    async def initialize_agents(self):
        """Initialize AI agents."""
        if not self.ordering_agent:
            # Start required services first
            await self.start_backend_server()
            await self.start_mcp_server()
            
            self.ordering_agent = PizzaOrderingAgent()
            print("✅ Ordering agent initialized")
            
        # Use scheduling agent for A2A communication and notifications
        if not self.scheduling_agent:
            self.scheduling_agent = PizzaSchedulingAgent()
            print("✅ Scheduling agent initialized for A2A communication")
    
    async def connect(self, websocket: WebSocket, client_id: str):
        """Connect a new client."""
        await websocket.accept()
        self.active_connections[client_id] = websocket
        
        # Initialize agents only once (not per client)
        if not self.ordering_agent or not self.scheduling_agent:
            await self.initialize_agents()
        
        print(f"✅ Client {client_id} connected")
    
    def disconnect(self, client_id: str):
        """Disconnect a client and clear their session."""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            
            # Clear the client's session from ordering agent
            if self.ordering_agent and hasattr(self.ordering_agent, 'session_manager'):
                self.ordering_agent.session_manager.clear_session(client_id)
            
            print(f"❌ Client {client_id} disconnected and session cleared")
    
    async def handle_status_update(self, message):
        """Handle status update A2A messages and notify connected users."""
        try:
            order_id = message.payload.get("order_id")
            action = message.payload.get("action")
            order_data = message.payload.get("order_data", {})
            
            # Find the pending order and its websocket connection
            if order_id in self.pending_orders:
                order_info = self.pending_orders[order_id]
                websocket = order_info.get("websocket")
                
                if websocket and action == "order_accepted":
                    # Send acceptance notification to user
                    items_text = ', '.join([f"{item['pizza']} ({item['size']})" for item in order_data.get('items', [])])
                    await websocket.send_json({
                        "type": "order_status",
                        "content": f"🎉 Great news! Your order #{order_id} has been accepted by the restaurant!\n\n"
                                 f"📋 Order Details:\n"
                                 f"• Items: {items_text}\n"
                                 f"• Total: ₹{order_data.get('total_price')}\n"
                                 f"• Prep Time: {order_data.get('prep_time')}\n"
                                 f"• Ready by: {order_data.get('estimated_ready')}\n"
                                 f"• Delivery: {order_data.get('estimated_delivery')}\n\n"
                                 f"📧 You'll receive email updates at your registered email address.",
                        "timestamp": tz_manager.format_for_storage(tz_manager.now_utc()),
                        "order_id": order_id
                    })
                    
                elif websocket and action == "order_ready":
                    # Send ready notification to user
                    await websocket.send_json({
                        "type": "order_status", 
                        "content": f"🍕 Your order #{order_id} is ready!\n\n"
                                 f"🚚 Your pizza is now out for delivery and should arrive soon.\n"
                                 f"📧 Check your email for detailed delivery information.",
                        "timestamp": tz_manager.format_for_storage(tz_manager.now_utc()),
                        "order_id": order_id
                    })
                    
                elif websocket and action == "order_rejected":
                    # Send rejection notification to user
                    await websocket.send_json({
                        "type": "order_status",
                        "content": f"😔 Sorry, your order #{order_id} was declined by the restaurant.\n\n"
                                 f"This could be due to ingredient availability or high demand.\n"
                                 f"Please try ordering again or contact the restaurant directly.",
                        "timestamp": tz_manager.format_for_storage(tz_manager.now_utc()),
                        "order_id": order_id
                    })
                    
                print(f"✅ Status update sent to user for order {order_id}: {action}")
            else:
                print(f"⚠️ No active connection found for order {order_id}")
                
        except Exception as e:
            print(f"❌ Error handling status update: {e}")
    
    def cleanup(self):
        """Cleanup background processes."""
        if self.mcp_server_process:
            self.mcp_server_process.terminate()
            self.mcp_server_process.wait()
            print("🧹 MCP server stopped")
            
        if self.backend_process:
            self.backend_process.terminate()
            self.backend_process.wait()
            print("🧹 Backend server stopped")
    
    async def process_message(self, websocket: WebSocket, message: Dict[str, Any], client_id: str):
        """Process incoming message from client."""
        try:
            user_message = message.get("content", "").strip()
            if not user_message:
                return
            
            print(f"📨 Processing message: {user_message}")
            
            # Process with ordering agent (pass client_id as session_id for context)
            result = await self.ordering_agent.process_request(user_message, session_id=client_id)
            
            # DEBUG: Log the actual result
            print(f"🔍 DEBUG - Result: {result}")
            print(f"🔍 DEBUG - Success: {result.get('success')}")
            print(f"🔍 DEBUG - Response: {result.get('response')}")
            
            if result.get("success"):
                # Check if we have a complete order
                handoff_message = result.get("handoff_message")
                
                # NEW: Check for A2A email collection messages
                if hasattr(result, 'get') and result.get("response") and "We'll send order updates to" in result.get("response", ""):
                    # Email was collected - send to scheduling agent for email processing
                    print("📧 Email collected, processing A2A message for scheduling agent")
                    
                    # Extract email from response
                    import re
                    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                    emails = re.findall(email_pattern, result.get("response", ""))
                    
                    if emails and self.scheduling_agent:
                        customer_email = emails[0]
                        
                        # Create A2A message for scheduling agent
                        from agents.communication import A2AMessage, A2AMessageType
                        email_message = A2AMessage(
                            type=A2AMessageType.STATUS_UPDATE,
                            from_agent="ordering_agent",
                            to_agent="scheduling_agent",
                            payload={
                                "action": "email_collected",
                                "customer_email": customer_email,
                                "order_id": f"email_{client_id[-8:]}",
                                "items": result.get("cart", {}).get("items", []) if result.get("cart") else []
                            },
                            correlation_id=client_id
                        )
                        
                        # Process with scheduling agent
                        try:
                            await self.scheduling_agent.process_order_message(email_message)
                            print(f"✅ Email message processed by scheduling agent: {customer_email}")
                        except Exception as e:
                            print(f"❌ Failed to process email with scheduling agent: {e}")
                
                if handoff_message:
                    # Order is complete - ask for customer email first
                    print("🗓️  Order placed, asking for customer email")
                    
                    # Ask customer for email before sending to restaurant
                    await websocket.send_json({
                        "type": "email_request",
                        "content": "🏪 Your order has been sent to the restaurant for approval.\n⏱️ While we wait, please provide your email address for order updates:",
                        "timestamp": tz_manager.format_for_storage(tz_manager.now_utc()),
                        "order_id": handoff_message.payload.get("order_id")
                    })
                    
                    # Store the order for later processing
                    order_id = handoff_message.payload.get("order_id")
                    if order_id:
                        self.pending_orders[order_id] = {
                            "websocket": websocket,
                            "client_id": client_id,
                            "order_data": handoff_message.payload,
                            "waiting_for_email": True
                        }
                else:
                    # Send regular agent response
                    await websocket.send_json({
                        "type": "bot_message",
                        "content": result.get("response", "I processed your message."),
                        "timestamp": tz_manager.format_for_storage(tz_manager.now_utc())
                    })
            else:
                # Order processing failed or needs clarification
                await websocket.send_json({
                    "type": "bot_message",
                    "content": result.get("response", "I'm having trouble understanding. Could you please clarify?"),
                    "timestamp": tz_manager.format_for_storage(tz_manager.now_utc())
                })
                
        except Exception as e:
            print(f"❌ Error processing message: {e}")
            await websocket.send_json({
                "type": "error",
                "content": "Sorry, I encountered an error. Please try again.",
                "timestamp": tz_manager.format_for_storage(tz_manager.now_utc())
            })

# Global chat manager
chat_manager = ChatManager()

@app.get("/")
async def get_chat_interface():
    """Serve the chat interface."""
    with open("chat_interface/static/index.html", "r") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for chat communication."""
    client_id = f"client_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
    
    try:
        await chat_manager.connect(websocket, client_id)
        
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Process the message
            if message.get("type") == "clear_chat":
                # Clear session when user clears chat
                if self.ordering_agent and hasattr(self.ordering_agent, 'session_manager'):
                    self.ordering_agent.session_manager.clear_session(client_id)
                
                await websocket.send_json({
                    "type": "chat_cleared",
                    "content": "Chat cleared. Starting fresh conversation.",
                    "timestamp": tz_manager.format_for_storage(tz_manager.now_utc())
                })
            else:
                # Normal message processing
                await chat_manager.process_message(websocket, message, client_id)
            
    except WebSocketDisconnect:
        chat_manager.disconnect(client_id)
    except Exception as e:
        print(f"❌ WebSocket error: {e}")
        chat_manager.disconnect(client_id)

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": tz_manager.format_for_storage(tz_manager.now_utc()),
        "active_connections": len(chat_manager.active_connections)
    }

@app.post("/api/notify-customer/{order_id}")
async def notify_customer_order_confirmed(order_id: str, status: str = "confirmed"):
    """Notify customer when business confirms/rejects their order"""
    if order_id in chat_manager.pending_orders:
        order_info = chat_manager.pending_orders[order_id]
        websocket = order_info["websocket"]
        order_data = order_info["order_data"]
        
        try:
            if status == "confirmed":
                # Business confirmed the order
                prep_time = order_data.get("prep_time", "20 mins")
                estimated_ready = order_data.get("estimated_ready", "")
                
                message = f"✅ Great news! Your order #{order_id} has been confirmed by the restaurant!\n\n🍕 Preparation time: {prep_time}\n⏰ Estimated ready: {estimated_ready}\n\nWe'll notify you when your order is ready for pickup/delivery!"
                
                await websocket.send_json({
                    "type": "order_confirmed",
                    "content": message,
                    "timestamp": tz_manager.format_for_storage(tz_manager.now_utc()),
                    "order_id": order_id,
                    "prep_time": prep_time,
                    "estimated_ready": estimated_ready
                })
                
            elif status == "rejected":
                # Business rejected the order
                message = f"😔 Sorry, your order #{order_id} couldn't be processed by the restaurant. This might be due to ingredient availability or high demand.\n\nWould you like to try ordering something else?"
                
                await websocket.send_json({
                    "type": "order_rejected", 
                    "content": message,
                    "timestamp": tz_manager.format_for_storage(tz_manager.now_utc()),
                    "order_id": order_id
                })
            
            # Remove from pending orders
            del chat_manager.pending_orders[order_id]
            
            return {"success": True, "message": f"Customer notified about order {order_id}"}
            
        except Exception as e:
            print(f"Error notifying customer: {e}")
            return {"success": False, "error": str(e)}
    
    return {"success": False, "error": "Order not found or customer disconnected"}

@app.post("/api/a2a-message")
async def handle_a2a_message(message_data: dict):
    """Handle A2A messages from business dashboard to scheduling agent"""
    try:
        from agents.communication import A2AMessage
        
        # Convert dict back to A2AMessage
        message = A2AMessage(**message_data)
        
        # Forward to scheduling agent if it exists
        if chat_manager.scheduling_agent and message.to_agent == "scheduling_agent":
            # Process the message through scheduling agent
            await chat_manager.scheduling_agent.process_order_message(message)
            return {"success": True, "message": "A2A message processed"}
        elif message.to_agent == "chat_interface":
            # Handle status updates for chat interface
            await chat_manager.handle_status_update(message)
            return {"success": True, "message": "Status update processed"}
        else:
            print(f"No target agent found for: {message.to_agent}")
            return {"success": False, "error": "Target agent not available"}
            
    except Exception as e:
        print(f"Error processing A2A message: {e}")
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    import uvicorn
    
    def signal_handler(signum, frame):
        """Handle shutdown signals."""
        print("\n🛑 Shutting down chat interface...")
        chat_manager.cleanup()
        sys.exit(0)
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("🚀 Starting Pizza Chat Interface Server...")
    print("📱 Chat Interface: http://localhost:8001")
    print("🔗 WebSocket: ws://localhost:8001/ws")
    print("❤️  Health Check: http://localhost:8001/health")
    print("🛑 Press Ctrl+C to stop all services")
    
    # Open browser automatically
    webbrowser.open("http://localhost:8001")
    
    try:
        uvicorn.run(
            "chat_server:app",
            host="0.0.0.0",
            port=8001,
            reload=False,  # Disable reload to prevent process issues
            log_level="info"
        )
    finally:
        chat_manager.cleanup()
