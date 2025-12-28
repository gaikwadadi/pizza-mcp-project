"""
Business Owner Dashboard for Pizza Restaurant
Fallback to direct database access for reliability
"""
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import sqlite3
from datetime import datetime
from pathlib import Path
import json
import sys
import os

# Add services to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from services.free_email_service import free_email_service
from services.free_push_service import free_push_service

app = FastAPI(title="Pizza Business Dashboard")

# Setup templates
templates = Jinja2Templates(directory="business_dashboard/templates")

# Direct database access (fallback)
DB_PATH = Path(__file__).parent.parent / "backend" / "pizza.db"

def get_db_connection():
    """Get database connection"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard page"""
    import httpx
    
    try:
        # Get all orders from backend API
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8000/orders", timeout=5.0)
            all_orders = response.json() if response.status_code == 200 else []
    except Exception as e:
        print(f"Failed to fetch orders from API: {e}")
        all_orders = []
    
    # Filter pending orders (need owner confirmation)
    pending_orders = [order for order in all_orders if order.get('status') == 'preparing']
    
    # Get recent orders (limit 20)
    recent_orders = all_orders[:20]
    
    # Calculate today's stats
    from datetime import datetime
    today = datetime.now().strftime('%Y-%m-%d')
    today_stats = {
        'total_orders': len([o for o in all_orders if o.get('created_at', '').startswith(today)]),
        'confirmed_orders': len([o for o in all_orders if o.get('status') == 'confirmed' and o.get('created_at', '').startswith(today)]),
        'pending_orders': len([o for o in all_orders if o.get('status') == 'preparing' and o.get('created_at', '').startswith(today)]),
        'completed_orders': len([o for o in all_orders if o.get('status') == 'completed' and o.get('created_at', '').startswith(today)])
    }
    
    return templates.TemplateResponse("dashboard_tabbed.html", {
        "request": request,
        "pending_orders": pending_orders,
        "stats": today_stats,
        "recent_orders": recent_orders
    })
    
    # Convert to list of dicts for template with simple IST time
    pending_orders = []
    for order in pending_orders_raw:
        from datetime import datetime
        
        # Simple approach: use current IST time for display
        now = datetime.now()
        display_time = now.strftime('%d %b %Y, %I:%M %p')
        
        pending_orders.append({
            'order_id': order[0],
            'customer_email': order[1],
            'total_amount': order[2],
            'status': order[3],
            'prep_time': order[4],
            'created_at': display_time,
            'confirmed_at': order[6],
            'rejected_at': order[7],
            'completed_at': order[8],
            'items_summary': order[9] or 'No items'
        })
    
    # Get today's stats
    today = datetime.now().strftime('%Y-%m-%d')
    today_stats = conn.execute("""
        SELECT 
            COUNT(*) as total_orders,
            SUM(CASE WHEN status = 'confirmed' THEN 1 ELSE 0 END) as confirmed_orders,
            SUM(CASE WHEN status = 'preparing' THEN 1 ELSE 0 END) as pending_orders,
            SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_orders
        FROM orders 
        WHERE DATE(created_at) = ?
    """, (today,)).fetchone()
    
    # Get recent activity - newest first
    recent_orders_raw = conn.execute("""
        SELECT o.*, GROUP_CONCAT(oi.pizza || ' (' || oi.size || ') x' || oi.quantity, ', ') as items_summary
        FROM orders o
        LEFT JOIN order_items oi ON o.order_id = oi.order_id
        GROUP BY o.order_id
        ORDER BY o.created_at DESC 
        LIMIT 20
    """).fetchall()
    
    # Convert to list of dicts for template with simple IST time
    recent_orders = []
    for order in recent_orders_raw:
        from datetime import datetime
        
        # Simple approach: use current IST time for display
        now = datetime.now()
        display_time = now.strftime('%d %b %Y, %I:%M %p')
        
        # Calculate delivery time (prep_time + 30 min delivery)
        prep_time = order[4] or 20  # default 20 min if None
        delivery_time = prep_time + 30
        expected_delivery = now.strftime('%I:%M %p')  # Simple current time + delivery
        
        recent_orders.append({
            'order_id': order[0],
            'customer_email': order[1],
            'total_amount': order[2],
            'status': order[3],
            'prep_time': prep_time,
            'created_at': display_time,
            'expected_delivery': expected_delivery,
            'confirmed_at': order[6],
            'rejected_at': order[7],
            'completed_at': order[8],
            'items_summary': order[9] or 'No items'
        })
    
    # Get menu items
    menu_items = conn.execute("""
        SELECT * FROM menu 
        ORDER BY name
    """).fetchall()
    
    # Parse sizes JSON for display
    parsed_menu = []
    for item in menu_items:
        item_dict = dict(item)
        try:
            sizes = json.loads(item_dict['sizes'])
            item_dict['sizes_display'] = ', '.join(sizes)
        except:
            item_dict['sizes_display'] = item_dict['sizes']
        parsed_menu.append(item_dict)
    
    conn.close()
    
    return templates.TemplateResponse("dashboard_tabbed.html", {
        "request": request,
        "pending_orders": pending_orders,
        "stats": dict(today_stats) if today_stats else {},
        "recent_orders": recent_orders
    })

from agents.communication import A2AMessage, A2AMessageType, A2AMessageBus

# Initialize A2A message bus
message_bus = A2AMessageBus()

# In-memory store for customer emails by order ID
customer_emails = {}

@app.post("/api/orders/{order_id}/confirm")
async def confirm_order(order_id: str):
    """Confirm order via backend API"""
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.post(f"http://localhost:8000/orders/{order_id}/confirm", timeout=5.0)
            return response.json() if response.status_code == 200 else {"error": response.text}
    except Exception as e:
        return {"error": str(e)}
    
    # Update order status to confirmed
    cursor = conn.execute("""
        UPDATE orders 
        SET status = 'confirmed', 
            confirmed_at = CURRENT_TIMESTAMP 
        WHERE order_id = ? AND status = 'preparing'
    """, (order_id,))
    
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Order not found or already processed")
    
    # Get customer email before closing connection
    order_row = conn.execute("SELECT customer_email FROM orders WHERE order_id = ?", (order_id,)).fetchone()
    customer_email = order_row[0] if order_row and order_row[0] else "test.customer@gmail.com"
    
    conn.commit()
    conn.close()
    
    # Try to notify customer via chat interface
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            await client.post(f"http://localhost:8001/api/notify-customer/{order_id}?status=confirmed")
    except Exception as e:
        print(f"Failed to notify customer: {e}")
    
    # Send FREE notifications to customer
    order_data = {
        'order_id': order_id,
        'items': [{'pizza': 'Pizza', 'size': 'medium', 'quantity': 1}],
        'total_price': 349,
        'prep_time': '20 mins',
        'estimated_ready': datetime.now().strftime('%d %b %Y, %I:%M %p')
    }
    
    # Send A2A message to scheduling agent for email notification
    await send_order_confirmed_message(order_id, customer_email, order_data)
    
    # FREE Web Push notification
    free_push_service.send_order_accepted_push(order_data)
    
    return {"success": True, "message": f"Order {order_id} confirmed, email notifications sent"}

@app.post("/api/orders/{order_id}/reject")
async def reject_order(order_id: str):
    """Reject order (owner declines)"""
    conn = get_db_connection()
    
    cursor = conn.execute("""
        UPDATE orders 
        SET status = 'rejected', 
            rejected_at = CURRENT_TIMESTAMP 
        WHERE order_id = ? AND status = 'preparing'
    """, (order_id,))
    
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Order not found or already processed")
    
    conn.commit()
    conn.close()
    
    # Try to notify customer via chat interface
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            await client.post(f"http://localhost:8001/api/notify-customer/{order_id}?status=rejected")
    except Exception as e:
        print(f"Failed to notify customer: {e}")
    
    return {"success": True, "message": f"Order {order_id} rejected and customer notified"}

@app.post("/api/orders/{order_id}/complete")
async def complete_order(order_id: str):
    """Mark order as completed (ready for delivery)"""
    conn = get_db_connection()
    
    # Get order details first
    order = conn.execute("""
        SELECT * FROM orders WHERE order_id = ?
    """, (order_id,)).fetchone()
    
    if not order:
        conn.close()
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Get order details before updating
    order_items = conn.execute("""
        SELECT oi.pizza, oi.size, oi.quantity 
        FROM order_items oi
        JOIN orders o ON oi.order_id = o.order_id
        WHERE o.order_id = ? AND o.status = 'confirmed'
    """, (order_id,)).fetchall()
    
    if not order_items:
        conn.close()
        raise HTTPException(status_code=404, detail="Order not found or not confirmed")
    # Get customer email before closing connection
    email_row = conn.execute("SELECT customer_email FROM orders WHERE order_id = ?", (order_id,)).fetchone()
    customer_email = email_row[0] if email_row and email_row[0] else "test.customer@gmail.com"
    
    cursor = conn.execute("""
        UPDATE orders 
        SET status = 'completed', 
            completed_at = CURRENT_TIMESTAMP 
        WHERE order_id = ? AND status = 'confirmed'
    """, (order_id,))
    
    conn.commit()
    conn.close()
    
    # Send FREE notifications that pizza is ready for delivery
    order_data = {
        'order_id': order_id,
        'items': [{'pizza': item[0], 'size': item[1], 'quantity': item[2]} for item in order_items]
    }
    
    # Send A2A message to scheduling agent for email notification
    await send_order_ready_message(order_id, customer_email, order_data)
    
    # FREE Web Push notification
    free_push_service.send_pizza_ready_push(order_data)
    
    return {"success": True, "message": f"Order {order_id} completed, email delivery notifications sent"}

async def send_order_confirmed_message(order_id: str, customer_email: str, order_data: dict):
    """Send A2A message to scheduling agent for order confirmation email"""
    try:
        message = A2AMessage(
            type=A2AMessageType.STATUS_UPDATE,
            from_agent="business_dashboard",
            to_agent="scheduling_agent",
            payload={
                "action": "order_confirmed",
                "order_id": order_id,
                "customer_email": customer_email,
                "order_data": order_data
            },
            correlation_id=f"business_{order_id}"
        )
        await message_bus.send_message(message)
    except Exception as e:
        print(f"Failed to send order confirmed message: {e}")

async def send_order_ready_message(order_id: str, customer_email: str, order_data: dict):
    """Send A2A message to scheduling agent for order ready email"""
    try:
        message = A2AMessage(
            type=A2AMessageType.STATUS_UPDATE,
            from_agent="business_dashboard", 
            to_agent="scheduling_agent",
            payload={
                "action": "order_ready",
                "order_id": order_id,
                "customer_email": customer_email,
                "order_data": order_data
            },
            correlation_id=f"business_{order_id}"
        )
        await message_bus.send_message(message)
    except Exception as e:
        print(f"Failed to send order ready message: {e}")

@app.post("/api/orders/{order_id}/email")
async def store_customer_email(order_id: str, email_data: dict):
    """Store customer email for order notifications"""
    customer_email = email_data.get("customer_email")
    if customer_email:
        customer_emails[order_id] = customer_email
        return {"success": True, "message": f"Email stored for order {order_id}"}
    return {"success": False, "message": "No email provided"}

@app.get("/api/orders")
async def get_orders():
    """Get orders with simple IST time display"""
    conn = get_db_connection()
    
    # Get orders with their items
    orders_with_items = conn.execute("""
        SELECT 
            o.*,
            GROUP_CONCAT(
                oi.pizza || ' (' || oi.size || ') x' || oi.quantity, 
                ', '
            ) as items_summary
        FROM orders o
        LEFT JOIN order_items oi ON o.order_id = oi.order_id
        GROUP BY o.order_id
        ORDER BY o.created_at DESC
    """).fetchall()
    
    # Convert to simple format with IST time
    result = []
    for order in orders_with_items:
        from datetime import datetime
        
        # Simple approach: show current IST time in 12-hour format
        now = datetime.now()
        display_time = now.strftime('%d %b %Y, %I:%M %p')
        
        # Calculate expected delivery time (prep + 30 min delivery)
        prep_time = order['prep_time'] or 20
        expected_delivery = now.strftime('%I:%M %p')
        
        order_dict = {
            'order_id': order['order_id'],
            'customer_email': order['customer_email'],
            'total_amount': order['total_amount'],
            'status': order['status'],
            'prep_time': prep_time,
            'created_at': display_time,
            'expected_delivery': expected_delivery,
            'items_summary': order['items_summary'] or 'No items'
        }
        
        # Get items for this order
        items = conn.execute("""
            SELECT pizza, size, quantity, price 
            FROM order_items 
            WHERE order_id = ?
        """, (order['order_id'],)).fetchall()
        
        order_dict['items'] = [dict(item) for item in items]
        result.append(order_dict)
    
    conn.close()
    return result

@app.get("/api/stats/today")
async def today_stats():
    """Get today's statistics"""
    conn = get_db_connection()
    today = datetime.now().strftime('%Y-%m-%d')
    
    stats = conn.execute("""
        SELECT 
            COUNT(*) as total_orders,
            SUM(CASE WHEN status = 'confirmed' THEN 1 ELSE 0 END) as confirmed_orders,
            SUM(CASE WHEN status = 'preparing' THEN 1 ELSE 0 END) as pending_orders,
            SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_orders,
            SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END) as rejected_orders
        FROM orders 
        WHERE DATE(created_at) = ?
    """, (today,)).fetchone()
    
    conn.close()
    
    return dict(stats) if stats else {}

if __name__ == "__main__":
    import uvicorn
    import webbrowser
    print("🏪 Starting Pizza Business Dashboard...")
    print("📊 Dashboard: http://localhost:8090")
    print("📋 Orders API: http://localhost:8090/api/orders")
    print("📈 Stats API: http://localhost:8090/api/stats/today")
    
    # Open browser automatically
    webbrowser.open("http://localhost:8090")
    
    uvicorn.run(app, host="0.0.0.0", port=8090)
