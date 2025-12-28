# Pizza MCP Project

🍕 **Automated OpenAPI to MCP Server transformation with AI agents for pizza ordering**

A complete demonstration of converting REST APIs to Model Context Protocol (MCP) servers with intelligent AI agents for conversational pizza ordering. Features multi-agent coordination, real-time chat interface, and production-ready architecture.

## 🌟 Key Features

- **🔄 Automated Transformation**: OpenAPI specifications → MCP servers
- **🤖 Intelligent AI Agents**: LangGraph-powered conversational ordering
- **💬 Multi-Agent Coordination**: Seamless handoffs between ordering and scheduling
- **🌐 Real-time Chat Interface**: WebSocket-based live conversations  
- **📊 Business Dashboard**: Order analytics and management
- **🕐 Indian Market Ready**: IST timezone, ₹ currency, 12-hour format
- **📧 Email Notifications**: Automated delivery confirmations
- **🛡️ Production Architecture**: Error handling, logging, session management

## 🚀 Quick Start

### 1. Setup Environment

```bash
# Clone and setup
git clone <repository-url>
cd pizza-mcp-project

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# or venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables

```bash
# Copy and configure environment
cp .env.example .env

# Required API Keys (edit .env):
# - GROQ_API_KEY: Get from https://console.groq.com/
# - Gmail credentials for email notifications
```

### 3. Initialize System

```bash
# Setup database
python scripts/setup_db.py

# Extract OpenAPI specification
python scripts/extract_openapi.py

# Generate MCP server from OpenAPI spec
python -m transformer.main --input specs/pizza_openapi.json
```

### 4. Start Services

```bash
# Terminal 1: Start Backend API
python backend/main.py

# Terminal 2: Start MCP Server  
python generated/pizza_mcp_server_http.py

# Terminal 3: Start Chat Interface
python chat_interface/chat_server.py

# Terminal 4: Start Business Dashboard
python business_dashboard/main.py
```

### 5. Run Complete Demo

```bash
# Automated demo with all scenarios
python scripts/run_demo.py
```

## 🏗️ System Architecture

### Core Components

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Chat UI       │    │  Business       │    │   Demo Script   │
│  (Port 8001)    │    │  Dashboard      │    │                 │
│                 │    │  (Port 8090)    │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
┌─────────────────────────────────────────────────────────────────┐
│                     AI AGENTS LAYER                             │
│  ┌─────────────────┐              ┌─────────────────┐           │
│  │ Ordering Agent  │◄────A2A─────►│Scheduling Agent │           │
│  │ (LangGraph)     │   Messages   │ (LangGraph)     │           │
│  └─────────────────┘              └─────────────────┘           │
└─────────────────────────────────────────────────────────────────┘
                                 │
┌─────────────────────────────────────────────────────────────────┐
│                    MCP INTEGRATION                              │
│  ┌─────────────────┐              ┌─────────────────┐           │
│  │  Pizza MCP      │    HTTP      │  MCP Server     │           │
│  │   Client        │◄────────────►│ (Port 3000)     │           │
│  └─────────────────┘              └─────────────────┘           │
└─────────────────────────────────────────────────────────────────┘
                                 │
┌─────────────────────────────────────────────────────────────────┐
│                   BACKEND SERVICES                              │
│  ┌─────────────────┐              ┌─────────────────┐           │
│  │   FastAPI       │              │   SQLite        │           │
│  │  (Port 8000)    │◄────────────►│   Database      │           │
│  └─────────────────┘              └─────────────────┘           │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **User Input** → Chat Interface → Ordering Agent
2. **Menu Requests** → MCP Client → MCP Server → Backend API
3. **Order Processing** → A2A Messages → Scheduling Agent  
4. **Delivery Coordination** → Email Service → Customer Notification
5. **Real-time Updates** → WebSocket → Dashboard & Chat UI

## 📁 Project Structure

```
pizza-mcp-project/
├── 🍕 backend/              # FastAPI pizza ordering API
│   ├── main.py              # API endpoints (12 endpoints)
│   ├── database.py          # SQLite database management
│   ├── models.py            # Pydantic data models
│   └── pizza.db             # SQLite database file
├── 🔄 transformer/          # OpenAPI → MCP transformer (CORE)
│   ├── main.py              # CLI transformation tool
│   ├── parser.py            # OpenAPI specification parser
│   ├── mapper.py            # Endpoint → MCP tool mapping
│   ├── generator.py         # MCP server code generation
│   ├── utils.py             # Transformation utilities
│   └── templates/           # Code generation templates
├── 🤖 agents/               # AI agents (ordering & scheduling)
│   ├── ordering_agent.py    # Main conversational agent (84KB)
│   ├── scheduling_agent.py  # Delivery coordination agent
│   ├── agent_base.py        # Shared agent infrastructure
│   ├── communication.py     # A2A messaging protocol
│   ├── session_manager.py   # Conversation state management
│   ├── smart_error_handler.py # Intelligent error recovery
│   └── intelligent_clarifier.py # Context-aware questions
├── 🔗 mcp_clients/          # MCP client utilities
│   ├── pizza_client.py      # HTTP MCP client (ACTIVE)
│   ├── client_factory.py    # External service factory (FUTURE)
│   └── external_client.py   # External MCP client base (FUTURE)
├── ⚙️ generated/            # Generated MCP servers
│   ├── pizza_mcp_server.py  # stdio MCP server (12 tools)
│   └── pizza_mcp_server_http.py # HTTP MCP server (12 tools)
├── 📊 specs/                # OpenAPI specifications  
│   ├── pizza_openapi.json   # Current API specification
│   └── pizza_openapi_formatted.json # Formatted version
├── 💬 chat_interface/       # Real-time chat interface
│   ├── chat_server.py       # WebSocket chat server
│   ├── static/              # Frontend assets (HTML/CSS/JS)
│   └── templates/           # Chat UI templates
├── 📈 business_dashboard/   # Order analytics dashboard
│   ├── main.py              # Dashboard server
│   ├── static/              # Dashboard assets
│   └── templates/           # Dashboard UI
├── 🛠️ scripts/             # Utility scripts
│   ├── setup_db.py          # Database initialization
│   ├── extract_openapi.py   # OpenAPI spec extraction
│   └── run_demo.py          # Complete system demo (16KB)
├── 🌐 services/             # External service integrations
│   └── free_email_service.py # Gmail SMTP notifications
├── ⏰ utils/                # Shared utilities
│   └── timezone_utils.py    # IST timezone management (4.6KB)
├── 📋 .env                  # Environment configuration
├── 📦 requirements.txt      # Python dependencies
└── 📖 README.md             # This file
```

## 🎯 Core Innovation: OpenAPI → MCP Transformation

### The Problem
Converting REST APIs to MCP (Model Context Protocol) servers manually is time-consuming and error-prone.

### Our Solution
Automated transformation pipeline that converts any OpenAPI 3.x specification into a fully functional MCP server.

### Transformation Process

```bash
# 1. Extract OpenAPI spec from running FastAPI
python scripts/extract_openapi.py
# → Generates specs/pizza_openapi.json (12 endpoints)

# 2. Transform to MCP server
python -m transformer.main --input specs/pizza_openapi.json
# → Generates generated/pizza_mcp_server.py (12 MCP tools)

# 3. Generated MCP tools automatically map to API endpoints:
# GET /menu        → get_menu() tool
# POST /orders     → create_orders() tool  
# GET /orders/{id} → get_orders() tool
# PUT /orders/{id} → update_orders() tool
# ... and 8 more tools
```

### Before vs After

**Before (Manual Integration):**
```python
# Manual API integration - lots of boilerplate
async def get_menu():
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:8000/menu")
        return response.json()
```

**After (Generated MCP Tools):**
```python
# Auto-generated MCP tool - clean and standardized
@server.call_tool()
async def get_menu_handler(arguments: dict) -> list[TextContent]:
    # Generated code handles HTTP calls, error handling, validation
    return await call_backend_api("GET", "/menu", arguments)
```

## 🤖 AI Agent Architecture

### Multi-Agent System

#### 1. **Ordering Agent** (Primary)
- **Technology**: LangGraph state machine + Groq LLM
- **Responsibilities**: 
  - Natural language order processing
  - Intent classification and clarification
  - Cart management and session state
  - Error recovery with smart suggestions
- **Features**:
  - Context-aware conversations
  - Multi-turn dialog support
  - Intelligent error handling
  - Session persistence

#### 2. **Scheduling Agent** (Secondary)  
- **Technology**: LangGraph workflow + Email integration
- **Responsibilities**:
  - Delivery time calculation
  - Email notification dispatch
  - Order status coordination
- **Features**:
  - IST timezone handling
  - Smart delivery windows
  - Automated notifications

#### 3. **Agent Communication**
- **Protocol**: A2A (Agent-to-Agent) messaging
- **Message Types**: ORDER_PLACED, SCHEDULE_CONFIRMED, STATUS_UPDATE
- **Benefits**: Loose coupling, scalable coordination

### Conversation Flow Example

```
User: "I want 2 large pepperoni pizzas"
├── Intent Classification: "add_to_cart"
├── Menu Validation: ✅ Pepperoni available
├── Size Confirmation: ✅ Large available  
├── Cart Update: 2x Large Pepperoni (₹1,200)
├── Order Confirmation: "Ready in 25 minutes"
└── A2A Message → Scheduling Agent → Email Notification
```

## 🌐 User Interfaces

### 1. **Chat Interface** (Port 8001)
- Real-time WebSocket communication
- Clean, responsive chat UI
- Message history and session management
- Mobile-friendly design

### 2. **Business Dashboard** (Port 8090)
- Live order tracking
- Sales analytics and metrics
- Order management tools
- Admin controls

### 3. **Demo Script** 
- Automated system demonstration
- Multiple conversation scenarios
- Performance metrics display
- Complete workflow testing

## 🔧 Technical Specifications

### **Backend API** (Port 8000)
- **Framework**: FastAPI with automatic OpenAPI generation
- **Database**: SQLite with SQLAlchemy ORM
- **Endpoints**: 12 REST endpoints covering full pizza ordering workflow
- **Features**: CORS enabled, input validation, error handling

### **MCP Integration**
- **Generated Servers**: Both stdio and HTTP variants
- **Tools**: 12 MCP tools auto-mapped from API endpoints
- **Protocols**: HTTP (production) and stdio (development)
- **Client**: Pure HTTP client with async operations

### **AI Agents**
- **LLM Provider**: Groq (llama-3.1-8b-instant)
- **Framework**: LangGraph for state management
- **Features**: Intent classification, error recovery, session management
- **Communication**: A2A messaging with correlation IDs

### **External Services**
- **Email**: Gmail SMTP for delivery notifications
- **Timezone**: IST (Asia/Kolkata) with 12-hour format
- **Currency**: Indian Rupees (₹) with local pricing

## 🎮 Demo Scenarios

### 1. **Simple Order**
```
User: "I want a large Margherita pizza"
→ Agent processes, confirms order, schedules delivery
→ Email notification sent
→ Dashboard updated in real-time
```

### 2. **Complex Order**  
```
User: "2 medium pepperoni and 1 large veggie pizza"
→ Multi-item cart management
→ Price calculation and confirmation
→ Delivery time optimization
```

### 3. **Error Recovery**
```
User: "I want a Hawaiian pizza"  # Not on menu
→ Agent suggests alternatives: "We have Veggie Supreme or BBQ Chicken"
→ Graceful error handling with options
```

### 4. **Clarification**
```
User: "I want pizza"  # Ambiguous
→ Agent asks: "What type and size pizza would you like?"
→ Context-aware follow-up questions
```

## 🚀 Getting Started - Detailed

### Prerequisites
- Python 3.11+
- Groq API key (free tier: 14,400 requests/day)
- Gmail account for email notifications (optional)
- 4GB RAM, 2GB disk space

### Environment Setup

1. **API Keys Configuration**:
```bash
# Required in .env:
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL_ID=llama-3.1-8b-instant

# Optional (for email notifications):
GMAIL_EMAIL=your_email@gmail.com  
GMAIL_APP_PASSWORD=your_app_password
```

2. **Service Ports**:
- Backend API: 8000
- MCP Server: 3000  
- Chat Interface: 8001
- Business Dashboard: 8090

### Development Workflow

1. **Make API Changes**: Edit `backend/main.py`
2. **Regenerate OpenAPI**: `python scripts/extract_openapi.py`
3. **Update MCP Server**: `python -m transformer.main --input specs/pizza_openapi.json`
4. **Test Integration**: `python scripts/run_demo.py`


## 🛡️ Production Features

### **Error Handling**
- Graceful degradation on service failures
- Smart error recovery with user-friendly messages
- Comprehensive logging and monitoring
- Retry mechanisms for external services

### **Security**
- Environment-based configuration
- Input validation and sanitization  
- CORS configuration for web interfaces
- API key management best practices

### **Scalability**
- Async/await throughout the stack
- Stateless agent design (where possible)
- Database connection pooling

## 🔮 Future Enhancements

### **Planned Features**
- Multi-language support (Hindi, English)
- Voice interface integration
- Payment gateway integration
- Real-time order tracking with maps
- Customer feedback and ratings
- Inventory management integration

### **Technical Improvements**
- Kubernetes deployment manifests
- Comprehensive test suite
- Performance monitoring dashboard
- A/B testing framework for agent responses
- Advanced analytics and ML insights

## 🤝 Contributing

### **Development Setup**
```bash
# Fork and clone the repository
git clone <your-fork-url>
cd pizza-mcp-project

# Create feature branch
git checkout -b feature/your-feature-name

# Make changes and test
python scripts/run_demo.py

# Submit pull request
```
## 📚 Documentation

### **Additional Resources**
- `Pizza_MCP_System_HLD_Diagram_Guide.txt`: Complete architecture guide
- Inline code documentation throughout the project
- OpenAPI specification: `specs/pizza_openapi.json`
- Environment template: `.env.example`

### **Learning Resources**
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [MCP Protocol Specification](https://modelcontextprotocol.io/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Groq API Documentation](https://console.groq.com/docs)

## 🐛 Troubleshooting

### **Common Issues**

1. **Port Already in Use**:
```bash
# Check what's using the port
lsof -i :8000
# Kill the process if needed
kill -9 <PID>
```

2. **Environment Variables Not Loaded**:
```bash
# Verify .env file exists and has correct format
cat .env | grep GROQ_API_KEY
```

3. **Agent Not Responding**:
```bash
# Check Groq API key and model availability
python -c "from agents.agent_base import AgentBase; print('✅ Agent setup OK')"
```

4. **MCP Server Connection Failed**:
```bash
# Verify MCP server is running
curl http://localhost:3000/tools
```

### **Debug Mode**
```bash
# Enable detailed logging
export LOG_LEVEL=DEBUG
python scripts/run_demo.py
```

## Acknowledgments

- **LangChain/LangGraph**: For the agent framework
- **FastAPI**: For the excellent API framework  
- **Groq**: For fast LLM inference
- **MCP Protocol**: For the standardized tool calling interface

---

## 🏢 About This Project

This Pizza MCP Project represents a comprehensive demonstration of enterprise-grade AI agent architecture and automated API integration. Built as a proof-of-concept for modern conversational AI systems, it showcases industry best practices in multi-agent coordination, real-time communication, and intelligent error handling.

The project serves as a reference implementation for organizations looking to integrate AI agents with existing REST APIs, demonstrating how to build scalable, production-ready conversational interfaces that maintain professional user experiences while handling complex business logic.

**Developed to advance the state of AI-powered API integration and demonstrate the practical applications of Model Context Protocol in enterprise environments.**

*This project showcases how modern AI agents can seamlessly integrate with existing APIs through automated transformation, creating intelligent, conversational interfaces for any REST API.*
