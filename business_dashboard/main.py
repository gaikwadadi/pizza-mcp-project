from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from datetime import datetime
import httpx

app = FastAPI(title="Pizza Business Dashboard")

# Setup templates
templates = Jinja2Templates(directory="business_dashboard/templates")

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard page - Using API calls only"""
    try:
        # Get all orders from backend API
        async with httpx.AsyncClient() as client:
            orders_response = await client.get("http://localhost:8000/orders", timeout=5.0)
            all_orders = orders_response.json() if orders_response.status_code == 200 else []
            
            # Get today's stats from backend API
            stats_response = await client.get("http://localhost:8000/stats/today", timeout=5.0)
            today_stats = stats_response.json() if stats_response.status_code == 200 else {}
            
    except Exception as e:
        print(f"Failed to fetch data from API: {e}")
        all_orders = []
        today_stats = {}
    
    # Filter orders by status
    pending_orders = [order for order in all_orders if order.get('status') == 'preparing']
    accepted_orders = [order for order in all_orders if order.get('status') == 'confirmed']
    rejected_orders = [order for order in all_orders if order.get('status') == 'rejected']
    
    # Get recent orders (limit 20)
    recent_orders = all_orders[:20]
    
    return templates.TemplateResponse("dashboard_tabbed.html", {
        "request": request,
        "pending_orders": pending_orders,
        "accepted_orders": accepted_orders,
        "rejected_orders": rejected_orders,
        "stats": today_stats,
        "recent_orders": recent_orders
    })

# Keep the rest of the business dashboard functionality for now
# (Order confirmation, rejection, completion will be Phase 2)

@app.post("/api/orders/{order_id}/confirm")
async def confirm_order(order_id: str):
    """Confirm order via backend API"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(f"http://localhost:8000/orders/{order_id}/confirm", timeout=5.0)
            
            if response.status_code == 200:
                return response.json()
            else:
                raise HTTPException(status_code=response.status_code, detail=response.text)
                
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/orders/{order_id}/reject")
async def reject_order(order_id: str):
    """Reject order via backend API"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(f"http://localhost:8000/orders/{order_id}/reject", timeout=5.0)
            
            if response.status_code == 200:
                return response.json()
            else:
                raise HTTPException(status_code=response.status_code, detail=response.text)
                
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/orders/{order_id}/complete")
async def complete_order(order_id: str):
    """Complete order via backend API"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(f"http://localhost:8000/orders/{order_id}/complete", timeout=5.0)
            
            if response.status_code == 200:
                return response.json()
            else:
                raise HTTPException(status_code=response.status_code, detail=response.text)
                
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/orders")
async def get_orders():
    """Get orders via backend API"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8000/orders", timeout=5.0)
            
            if response.status_code == 200:
                return response.json()
            else:
                raise HTTPException(status_code=response.status_code, detail=response.text)
                
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stats/today")
async def today_stats():
    """Get today's stats via backend API"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8000/stats/today", timeout=5.0)
            
            if response.status_code == 200:
                return response.json()
            else:
                raise HTTPException(status_code=response.status_code, detail=response.text)
                
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    import webbrowser
    import threading
    import time
    
    def open_browser():
        time.sleep(2)  # Wait for server to start
        webbrowser.open("http://localhost:8090")
    
    print("🏪 Starting Pizza Business Dashboard...")
    print("📊 Dashboard: http://localhost:8090")
    
    # Open browser in background thread
    threading.Thread(target=open_browser, daemon=True).start()
    
    uvicorn.run(app, host="0.0.0.0", port=8090)
