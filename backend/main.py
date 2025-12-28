from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List
from models import MenuItem, MenuItemCreate, OrderRequest, OrderResponse, OrderStatus
from database import init_db, get_menu, create_order, get_order, add_menu_item, get_db_connection
from config import API_TITLE, API_DESCRIPTION, API_VERSION

# Import notification services
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from services.free_email_service import FreeEmailService
from services.free_push_service import FreeWebPushService

# Initialize notification services
email_service = FreeEmailService()
push_service = FreeWebPushService()

async def send_a2a_notification(order_id: str, notification_type: str, order_data: dict):
    """Send A2A notification to chat interface"""
    try:
        import httpx
        from agents.communication import A2AMessage, A2AMessageType
        
        # Create A2A message
        message = A2AMessage(
            type=A2AMessageType.STATUS_UPDATE,
            from_agent="backend",
            to_agent="chat_interface",
            payload={
                "action": notification_type,
                "order_id": order_id,
                "order_data": order_data
            },
            correlation_id=order_id
        )
        
        # Send to chat interface
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8001/api/a2a-message",
                json=message.dict(),
                timeout=5.0
            )
            if response.status_code == 200:
                print(f"✅ A2A notification sent: {notification_type} for order {order_id}")
            else:
                print(f"❌ Failed to send A2A notification: {response.status_code}")
                
    except Exception as e:
        print(f"❌ Error sending A2A notification: {e}")

async def send_order_notifications(order_id: str, notification_type: str):
    """Send notifications for order status changes"""
    try:
        # Get order details
        conn = get_db_connection()
        order = conn.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,)).fetchone()
        
        if not order:
            return False
            
        customer_email = order['customer_email']
        
        # Skip notifications if no customer email provided
        if not customer_email:
            print(f"No customer email for order {order_id}, skipping notifications")
            return False
        
        # Get order items
        items = conn.execute("""
            SELECT pizza, size, quantity, price 
            FROM order_items 
            WHERE order_id = ?
        """, (order_id,)).fetchall()
        
        conn.close()
        
        # Prepare order data using stored estimated times
        from datetime import datetime
        
        # Format stored estimated times for display
        estimated_ready_formatted = ""
        estimated_delivery_formatted = ""
        
        if order['estimated_ready']:
            try:
                estimated_ready_dt = datetime.fromisoformat(order['estimated_ready'])
                estimated_ready_formatted = estimated_ready_dt.strftime('%d %b %Y, %I:%M %p')
            except:
                estimated_ready_formatted = "20 mins from order time"
                
        if order['estimated_delivery']:
            try:
                estimated_delivery_dt = datetime.fromisoformat(order['estimated_delivery'])
                estimated_delivery_formatted = estimated_delivery_dt.strftime('%I:%M %p')
            except:
                estimated_delivery_formatted = "35 mins from order time"
        
        order_data = {
            'order_id': order_id,
            'items': [{'pizza': item['pizza'], 'size': item['size'], 'quantity': item['quantity']} for item in items],
            'total_price': order['total_amount'],
            'prep_time': order['prep_time'] or '20 mins',
            'estimated_ready': estimated_ready_formatted,
            'estimated_delivery': estimated_delivery_formatted
        }
        
        # Send notifications based on type
        if notification_type == "confirmed":
            email_service.send_order_accepted_email(customer_email, order_data)
            push_service.send_order_accepted_push(order_data)
            
            # Send A2A message to chat interface for user notification
            await send_a2a_notification(order_id, "order_accepted", order_data)
            
        elif notification_type == "completed":
            email_service.send_pizza_ready_email(customer_email, order_data)
            push_service.send_pizza_ready_push(order_data)
            
            # Send A2A message to chat interface for user notification
            await send_a2a_notification(order_id, "order_ready", order_data)
            
        elif notification_type == "rejected":
            email_service.send_order_rejected_email(customer_email, order_data)
            push_service.send_order_rejected_push(order_data)
            
            # Send A2A message to chat interface for user notification
            await send_a2a_notification(order_id, "order_rejected", order_data)
            
        return True
            
    except Exception as e:
        print(f"Failed to send notifications: {e}")
        return False

app = FastAPI(
    title=API_TITLE,
    description=API_DESCRIPTION,
    version=API_VERSION
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    init_db()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "Pizza Backend"}

@app.get("/menu", response_model=List[MenuItem])
async def get_pizza_menu():
    """Get all available pizzas"""
    return get_menu()

@app.post("/orders", response_model=OrderResponse)
async def create_pizza_order(order: OrderRequest):
    """Create a new pizza order with multiple items"""
    menu = get_menu()
    pizza_names = [item["name"] for item in menu]
    
    # Validate all items
    for item in order.items:
        if item.pizza not in pizza_names:
            raise HTTPException(status_code=400, detail=f"Pizza '{item.pizza}' not found")
        
        pizza_item = next(menu_item for menu_item in menu if menu_item["name"] == item.pizza)
        if item.size not in pizza_item["sizes"]:
            raise HTTPException(status_code=400, detail=f"Invalid size '{item.size}' for {item.pizza}")
        
        # Set price if not provided
        if item.price == 0:
            item.price = pizza_item["price"]
    
    # Convert to dict format for database
    items_data = [item.dict() for item in order.items]
    order_id = create_order(items_data, order.customer_email)
    order_data = get_order(order_id)
    
    return OrderResponse(**order_data)

@app.get("/orders/{order_id}", response_model=OrderStatus)
async def get_order_status(order_id: str):
    """Get order status by ID"""
    order_data = get_order(order_id)
    if not order_data:
        raise HTTPException(status_code=404, detail="Order not found")
    
    return OrderStatus(**order_data)

@app.post("/admin/menu", response_model=MenuItem, status_code=201)
async def add_menu_item_endpoint(menu_item: MenuItemCreate):
    """Add new menu item (Admin only)"""
    try:
        created_item = add_menu_item(
            name=menu_item.name,
            price=menu_item.price,
            sizes=menu_item.sizes,
            description=menu_item.description
        )
        return MenuItem(**created_item)
    except ValueError as e:
        # Handle duplicate name error
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        # Handle other database errors
        raise HTTPException(status_code=500, detail="Failed to create menu item")

@app.get("/orders")
async def get_all_orders():
    """Get all orders with proper schema"""
    try:
        conn = get_db_connection()
        
        # Get orders with their items (matching the business dashboard format)
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
        
        # Convert to proper format
        result = []
        for order in orders_with_items:
            from datetime import datetime
            
            # Use stored estimated times if available, otherwise fallback
            estimated_ready_display = ""
            estimated_delivery_display = ""
            
            if order['estimated_ready']:
                try:
                    estimated_ready_dt = datetime.fromisoformat(order['estimated_ready'])
                    estimated_ready_display = estimated_ready_dt.strftime('%d %b %Y, %I:%M %p')
                except:
                    estimated_ready_display = "20 mins from order"
            else:
                estimated_ready_display = "20 mins from order"
                
            if order['estimated_delivery']:
                try:
                    estimated_delivery_dt = datetime.fromisoformat(order['estimated_delivery'])
                    estimated_delivery_display = estimated_delivery_dt.strftime('%I:%M %p')
                except:
                    estimated_delivery_display = "35 mins from order"
            else:
                estimated_delivery_display = "35 mins from order"
            
            order_dict = {
                'order_id': order['order_id'],
                'customer_email': order['customer_email'],
                'total_amount': order['total_amount'],
                'status': order['status'],
                'prep_time': order['prep_time'] or '20 mins',
                'created_at': estimated_ready_display,
                'expected_delivery': estimated_delivery_display,
                'estimated_ready': estimated_ready_display,
                'estimated_delivery': estimated_delivery_display,
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
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/orders/{order_id}")
async def update_order_status(order_id: str, status_update: dict):
    """Update order status"""
    try:
        new_status = status_update.get("status")
        if not new_status:
            raise HTTPException(status_code=400, detail="Status is required")
        
        # Update order in database
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE orders 
            SET status = ? 
            WHERE order_id = ?
        """, (new_status, order_id))
        
        if cursor.rowcount == 0:
            conn.close()
            raise HTTPException(status_code=404, detail="Order not found")
        
        conn.commit()
        conn.close()
        
        return {"success": True, "message": f"Order {order_id} updated to {new_status}"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/orders/{order_id}/email")
async def update_order_email(order_id: str, email_data: dict):
    """Update order with customer email"""
    customer_email = email_data.get("customer_email")
    if not customer_email:
        raise HTTPException(status_code=400, detail="Customer email is required")
    
    # Update order in database
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "UPDATE orders SET customer_email = ? WHERE order_id = ?",
        (customer_email, order_id)
    )
    
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Order not found")
    
    conn.commit()
    conn.close()
    
    return {"success": True, "message": f"Customer email updated for order {order_id}"}

@app.post("/orders/{order_id}/confirm")
async def confirm_order(order_id: str):
    """Confirm order (business accepts) with notifications"""
    try:
        conn = get_db_connection()
        
        # Update order status with timestamp
        cursor = conn.execute("""
            UPDATE orders 
            SET status = 'confirmed', confirmed_at = CURRENT_TIMESTAMP 
            WHERE order_id = ? AND status = 'preparing'
        """, (order_id,))
        
        if cursor.rowcount == 0:
            conn.close()
            raise HTTPException(status_code=404, detail="Order not found or already processed")
        
        conn.commit()
        conn.close()
        
        # Send notifications
        notification_sent = await send_order_notifications(order_id, "confirmed")
        
        message = f"Order {order_id} confirmed"
        if notification_sent:
            message += " and notifications sent"
        
        return {"success": True, "message": message, "order_id": order_id}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/orders/{order_id}/reject")
async def reject_order(order_id: str):
    """Reject order (business declines)"""
    try:
        conn = get_db_connection()
        
        # Update order status with timestamp
        cursor = conn.execute("""
            UPDATE orders 
            SET status = 'rejected', rejected_at = CURRENT_TIMESTAMP 
            WHERE order_id = ? AND status = 'preparing'
        """, (order_id,))
        
        if cursor.rowcount == 0:
            conn.close()
            raise HTTPException(status_code=404, detail="Order not found or already processed")
        
        conn.commit()
        conn.close()
        
        # Send rejection notifications
        notification_sent = await send_order_notifications(order_id, "rejected")
        
        message = f"Order {order_id} rejected"
        if notification_sent:
            message += " and customer notified"
        
        return {"success": True, "message": message, "order_id": order_id}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/orders/{order_id}/complete")
async def complete_order(order_id: str):
    """Mark order as completed (ready for delivery) with notifications"""
    try:
        conn = get_db_connection()
        
        # Update order status with timestamp
        cursor = conn.execute("""
            UPDATE orders 
            SET status = 'completed', completed_at = CURRENT_TIMESTAMP 
            WHERE order_id = ? AND status = 'confirmed'
        """, (order_id,))
        
        if cursor.rowcount == 0:
            conn.close()
            raise HTTPException(status_code=404, detail="Order not found or not confirmed")
        
        conn.commit()
        conn.close()
        
        # Send notifications
        notification_sent = await send_order_notifications(order_id, "completed")
        
        message = f"Order {order_id} completed"
        if notification_sent:
            message += " and notifications sent"
        
        return {"success": True, "message": message, "order_id": order_id}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats/today")
async def get_today_stats():
    """Get today's statistics"""
    from datetime import datetime
    
    try:
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
        
        return {
            "total_orders": stats[0] or 0,
            "confirmed_orders": stats[1] or 0,
            "pending_orders": stats[2] or 0,
            "completed_orders": stats[3] or 0,
            "rejected_orders": stats[4] or 0
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
