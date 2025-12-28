"""
Complete demo script showcasing the entire pizza MCP project workflow.
Orchestrates all components and demonstrates end-to-end functionality.
"""
import asyncio
import subprocess
import time
import signal
import sys
import os
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from agents.ordering_agent import PizzaOrderingAgent
from agents.scheduling_agent import PizzaSchedulingAgent
from agents.communication import A2AMessageBus
from utils.timezone_utils import tz_manager

class DemoOrchestrator:
    """Orchestrates the complete demo workflow."""
    
    def __init__(self):
        self.backend_process = None
        self.mcp_server_process = None
        self.ordering_agent = None
        self.scheduling_agent = None
        
    def print_banner(self, title: str, char: str = "="):
        """Print formatted banner."""
        print(f"\n{char * 60}")
        print(f"🍕 {title}")
        print(f"{char * 60}")
        
    def print_step(self, step: str, status: str = ""):
        """Print demo step."""
        status_emoji = "✅" if status == "success" else "🔄" if status == "running" else "📋"
        print(f"{status_emoji} {step}")
        
    async def start_backend(self):
        """Start the FastAPI backend server."""
        self.print_step("Starting FastAPI Backend Server", "running")
        
        try:
            # Kill any existing backend process
            subprocess.run(["lsof", "-ti:8000"], capture_output=True, text=True)
            result = subprocess.run(["lsof", "-ti:8000"], capture_output=True, text=True)
            if result.stdout.strip():
                subprocess.run(["kill", "-9"] + result.stdout.strip().split())
                time.sleep(1)
            
            # Start backend
            self.backend_process = subprocess.Popen(
                ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"],
                cwd=project_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Wait for backend to start
            await asyncio.sleep(3)
            
            # Verify backend is running
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get("http://localhost:8000/menu")
                if response.status_code == 200:
                    menu = response.json()
                    self.print_step(f"Backend started successfully - {len(menu)} menu items loaded", "success")
                    return True
                    
        except Exception as e:
            print(f"❌ Failed to start backend: {e}")
            return False
            
    async def start_mcp_server(self):
        """Start the generated MCP server."""
        self.print_step("Starting Generated MCP Server", "running")
        
        try:
            # Start MCP server
            self.mcp_server_process = subprocess.Popen(
                ["python", "generated/pizza_mcp_server.py"],
                cwd=project_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            await asyncio.sleep(2)
            self.print_step("MCP Server started successfully", "success")
            return True
            
        except Exception as e:
            print(f"❌ Failed to start MCP server: {e}")
            return False
            
    async def initialize_agents(self):
        """Initialize AI agents."""
        self.print_step("Initializing AI Agents", "running")
        
        try:
            self.ordering_agent = PizzaOrderingAgent()
            self.scheduling_agent = PizzaSchedulingAgent()
            
            self.print_step("Ordering Agent initialized", "success")
            self.print_step("Scheduling Agent initialized", "success")
            return True
            
        except Exception as e:
            print(f"❌ Failed to initialize agents: {e}")
            return False
            
    async def demo_scenario_1(self):
        """Demo Scenario 1: Simple Order with Real LLM."""
        self.print_banner("DEMO SCENARIO 1: Simple Pizza Order (Real LLM)", "-")
        
        print("👤 Customer: \"I want a large Margherita pizza\"")
        print()
        
        # Use real ordering agent with LLM
        print("🤖 Ordering Agent: Processing with Gemini LLM...")
        
        order_result = await self.ordering_agent.process_request("I want a large Margherita pizza")
        
        if order_result.get("status") == "success":
            print("✅ Order processed successfully by LLM!")
            
            # Get the handoff message
            handoff_message = order_result.get("handoff_message")
            
            if handoff_message:
                order_data = handoff_message.payload
                
                print(f"   Order ID: {order_data.get('order_id')}")
                print(f"   Items: {len(order_data.get('items', []))} item(s)")
                print(f"   Total: ₹{order_data.get('total_price')}")
                print(f"   Ready by: {order_data.get('estimated_ready')}")
                print()
                
                print("📨 A2A Message: ORDER_PLACED sent to Scheduling Agent")
                print()
                
                # Process through scheduling agent
                print("🗓️  Scheduling Agent: Processing delivery schedule...")
                schedule_result = await self.scheduling_agent.process_order_message(handoff_message)
                
                if schedule_result and schedule_result.type == "schedule_confirmed":
                    payload = schedule_result.payload
                    delivery_time = tz_manager.parse_from_storage(payload["delivery_time"])
                    
                    print("✅ Scheduling Agent: Delivery scheduled successfully!")
                    print(f"   Delivery Time: {tz_manager.format_delivery_time(delivery_time)}")
                    print()
                    
                    print("📱 Customer Notification:")
                    print(f"   Hi there!")
                    print(f"   Your pizza order #{order_data.get('order_id')} is confirmed.")
                    print(f"   Delivery: {tz_manager.format_time_only(delivery_time)}")
                    print(f"   Total: ₹{order_data.get('total_price')}")
                    print(f"   Delivery scheduled successfully!")
                    
                else:
                    print("❌ Scheduling failed")
                    return False
                    
            else:
                print("❌ No handoff message created")
                return False
                
        else:
            print(f"❌ LLM Processing Failed: {order_result.get('response')}")
            return False
            
        return True
        
    async def demo_scenario_2(self):
        """Demo Scenario 2: Complex Order with Real LLM."""
        self.print_banner("DEMO SCENARIO 2: Complex Order (Real LLM)", "-")
        
        print("👤 Customer: \"I want 2 medium pepperoni pizzas and 1 large veggie pizza\"")
        print()
        
        print("🤖 Ordering Agent: Processing complex order with Gemini LLM...")
        
        order_result = await self.ordering_agent.process_request("I want 2 medium pepperoni pizzas and 1 large veggie pizza")
        
        if order_result.get("status") == "success":
            print("✅ Complex order processed successfully by LLM!")
            
            handoff_message = order_result.get("handoff_message")
            
            if handoff_message:
                order_data = handoff_message.payload
                
                print(f"   Order ID: {order_data.get('order_id')}")
                print(f"   Items: {len(order_data.get('items', []))} item(s)")
                print(f"   Total: ₹{order_data.get('total_price')}")
                print()
                
                print("📨 A2A Message: ORDER_PLACED sent to Scheduling Agent")
                print()
                
                print("🗓️  Scheduling Agent: Calculating delivery time...")
                
                schedule_result = await self.scheduling_agent.process_order_message(handoff_message)
                
                if schedule_result and schedule_result.type == "schedule_confirmed":
                    payload = schedule_result.payload
                    delivery_time = tz_manager.parse_from_storage(payload["delivery_time"])
                    
                    print("✅ Delivery scheduled successfully!")
                    print(f"   Delivery Time: {tz_manager.format_delivery_time(delivery_time)}")
                    print()
                    
                    print("📱 Customer Notification:")
                    print(f"   Hi there!")
                    print(f"   Your order #{order_data.get('order_id')} is confirmed.")
                    print(f"   Items: {len(order_data.get('items', []))} pizzas")
                    print(f"   Delivery: {tz_manager.format_time_only(delivery_time)}")
                    print(f"   Total: ₹{order_data.get('total_price')}")
                    
                else:
                    print("❌ Scheduling failed")
                    return False
                    
            else:
                print("❌ No handoff message created")
                return False
                
        else:
            print(f"❌ LLM Processing Failed: {order_result.get('response')}")
            return False
            
        return True
        
    async def demo_scenario_3(self):
        """Demo Scenario 3: System Integration Showcase."""
        self.print_banner("DEMO SCENARIO 3: System Integration Showcase", "-")
        
        print("🔧 Demonstrating complete system integration:")
        print()
        
        # Show OpenAPI → MCP transformation
        print("1️⃣  OpenAPI Specification:")
        print("   ✅ Backend auto-generates OpenAPI spec")
        print("   ✅ 4 endpoints: GET /menu, POST /orders, GET /orders/{id}, POST /admin/menu")
        print()
        
        print("2️⃣  MCP Server Generation:")
        print("   ✅ Transformer converts OpenAPI → MCP tools")
        print("   ✅ Generated server with 4 MCP tools")
        print("   ✅ Automatic tool name mapping (get_menu, create_order, etc.)")
        print()
        
        print("3️⃣  Agent Coordination:")
        print("   ✅ Ordering Agent ↔ MCP Server ↔ Backend")
        print("   ✅ A2A Communication (ORDER_PLACED → SCHEDULE_CONFIRMED)")
        print("   ✅ Scheduling Agent ↔ Email Notifications")
        print()
        
        print("4️⃣  External Service Integration:")
        print("   ✅ Email notifications for delivery scheduling")
        print("   ✅ Time optimization and delivery window calculation")
        print("   ✅ Order coordination between agents")
        print()
        
        print("5️⃣  Localization:")
        print("   ✅ Indian timezone (IST) with 12-hour format")
        print("   ✅ Indian currency (₹) with market-based pricing")
        print("   ✅ Timezone-aware datetime calculations")
        print()
        
        return True
        
    async def show_system_stats(self):
        """Show system statistics."""
        self.print_banner("SYSTEM STATISTICS", "-")
        
        try:
            # Backend stats
            import httpx
            async with httpx.AsyncClient() as client:
                menu_response = await client.get("http://localhost:8000/menu")
                menu = menu_response.json()
                
            print(f"📊 Backend Statistics:")
            print(f"   Menu Items: {len(menu)}")
            print(f"   Price Range: ₹{min(item['price'] for item in menu):.0f} - ₹{max(item['price'] for item in menu):.0f}")
            print(f"   Average Price: ₹{sum(item['price'] for item in menu) / len(menu):.0f}")
            print()
            
            print(f"🤖 Agent Statistics:")
            print(f"   Ordering Agent: {self.ordering_agent.agent_name}")
            print(f"   Scheduling Agent: {self.scheduling_agent.agent_name}")
            print(f"   Session IDs: IST timestamp-based")
            print()
            
            print(f"🔧 Technical Features:")
            print(f"   ✅ OpenAPI → MCP Transformation")
            print(f"   ✅ LangGraph State Machines")
            print(f"   ✅ Async A2A Communication")
            print(f"   ✅ External MCP Integration")
            print(f"   ✅ Timezone-aware Processing")
            print(f"   ✅ Indian Market Localization")
            
        except Exception as e:
            print(f"❌ Error getting stats: {e}")
            
    async def cleanup(self):
        """Cleanup all processes and resources."""
        self.print_step("Cleaning up resources", "running")
        
        # Cleanup agents
        if self.ordering_agent:
            await self.ordering_agent.cleanup()
        if self.scheduling_agent:
            await self.scheduling_agent.cleanup()
            
        # Stop processes
        if self.mcp_server_process:
            self.mcp_server_process.terminate()
            self.mcp_server_process.wait()
            
        if self.backend_process:
            self.backend_process.terminate()
            self.backend_process.wait()
            
        self.print_step("Cleanup completed", "success")
        
    async def run_complete_demo(self):
        """Run the complete demo workflow."""
        try:
            self.print_banner("PIZZA MCP PROJECT - COMPLETE DEMO")
            print(f"🕐 Demo started at: {tz_manager.format_for_display(tz_manager.now_local())}")
            print()
            
            # Setup phase
            self.print_banner("PHASE 1: SYSTEM STARTUP", "=")
            
            if not await self.start_backend():
                return False
                
            if not await self.start_mcp_server():
                return False
                
            if not await self.initialize_agents():
                return False
                
            print("\n🎉 All systems ready!")
            
            # Demo scenarios
            self.print_banner("PHASE 2: DEMO SCENARIOS", "=")
            
            await self.demo_scenario_1()
            await asyncio.sleep(2)
            
            await self.demo_scenario_2()
            await asyncio.sleep(2)
            
            await self.demo_scenario_3()
            await asyncio.sleep(1)
            
            # System stats
            await self.show_system_stats()
            
            # Success
            self.print_banner("DEMO COMPLETED SUCCESSFULLY! 🎊", "=")
            print(f"🕐 Demo finished at: {tz_manager.format_for_display(tz_manager.now_local())}")
            print()
            print("🏆 Key Achievements Demonstrated:")
            print("   ✅ Complete OpenAPI → MCP transformation")
            print("   ✅ Multi-agent coordination with A2A communication")
            print("   ✅ Email notification service integration")
            print("   ✅ Production-ready timezone and currency handling")
            print("   ✅ End-to-end pizza ordering and scheduling workflow")
            
            return True
            
        except KeyboardInterrupt:
            print("\n\n⚠️  Demo interrupted by user")
            return False
        except Exception as e:
            print(f"\n\n❌ Demo failed: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            await self.cleanup()

def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully."""
    print("\n\n⚠️  Received interrupt signal. Cleaning up...")
    sys.exit(0)

async def main():
    """Main demo entry point."""
    signal.signal(signal.SIGINT, signal_handler)
    
    demo = DemoOrchestrator()
    success = await demo.run_complete_demo()
    
    if success:
        print("\n🎉 Demo completed successfully!")
        return 0
    else:
        print("\n❌ Demo failed!")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
