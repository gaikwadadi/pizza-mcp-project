import sqlite3
import json
from pathlib import Path

DB_PATH = Path(__file__).parent / "pizza.db"

def get_db_connection():
    """Get database connection with row factory"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize database with tables and seed data"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create tables
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS menu (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            sizes TEXT NOT NULL,
            description TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            order_id TEXT PRIMARY KEY,
            customer_email TEXT,
            total_amount REAL DEFAULT 0,
            status TEXT DEFAULT 'preparing',
            prep_time TEXT DEFAULT '20 mins',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            confirmed_at TIMESTAMP,
            rejected_at TIMESTAMP,
            completed_at TIMESTAMP
        )
    """)
    
    # Migration: Add missing columns to existing tables
    try:
        cursor.execute("ALTER TABLE orders ADD COLUMN confirmed_at TIMESTAMP")
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    try:
        cursor.execute("ALTER TABLE orders ADD COLUMN rejected_at TIMESTAMP")
    except sqlite3.OperationalError:
        pass  # Column already exists
        
    try:
        cursor.execute("ALTER TABLE orders ADD COLUMN completed_at TIMESTAMP")
    except sqlite3.OperationalError:
        pass  # Column already exists
        
    try:
        cursor.execute("ALTER TABLE orders ADD COLUMN estimated_ready TIMESTAMP")
    except sqlite3.OperationalError:
        pass  # Column already exists
        
    try:
        cursor.execute("ALTER TABLE orders ADD COLUMN estimated_delivery TIMESTAMP")
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id TEXT NOT NULL,
            pizza TEXT NOT NULL,
            size TEXT NOT NULL,
            quantity INTEGER DEFAULT 1,
            price REAL DEFAULT 0,
            FOREIGN KEY (order_id) REFERENCES orders (order_id)
        )
    """)
    
    # Seed menu data
    cursor.execute("SELECT COUNT(*) FROM menu")
    if cursor.fetchone()[0] == 0:
        menu_items = [
            ("Margherita", 12.99, '["small", "medium", "large"]', "Classic tomato sauce, mozzarella, fresh basil"),
            ("Pepperoni", 14.99, '["small", "medium", "large"]', "Tomato sauce, mozzarella, pepperoni"),
            ("Veggie", 13.99, '["small", "medium", "large"]', "Tomato sauce, mozzarella, bell peppers, mushrooms, onions"),
            ("BBQ Chicken", 16.99, '["small", "medium", "large"]', "BBQ sauce, mozzarella, grilled chicken, red onions")
        ]
        cursor.executemany("INSERT INTO menu (name, price, sizes, description) VALUES (?, ?, ?, ?)", menu_items)
    
    conn.commit()
    conn.close()

def get_menu():
    """Get all menu items"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM menu")
    items = cursor.fetchall()
    conn.close()
    
    return [
        {
            "id": item[0],
            "name": item[1],
            "price": item[2],
            "sizes": json.loads(item[3]),
            "description": item[4]
        }
        for item in items
    ]

def create_order(items: list, customer_email: str = None):
    """Create new order with multiple items and calculate estimated times"""
    import uuid
    from datetime import datetime, timedelta
    
    order_id = str(uuid.uuid4())[:8]
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Calculate total amount
    total_amount = sum(item.get('price', 0) * item.get('quantity', 1) for item in items)
    
    # Calculate estimated times
    now = datetime.now()
    prep_minutes = 20  # Default preparation time
    delivery_minutes = 15  # Default delivery time after preparation
    
    estimated_ready = now + timedelta(minutes=prep_minutes)
    estimated_delivery = estimated_ready + timedelta(minutes=delivery_minutes)
    
    # Create main order with estimated times
    cursor.execute(
        """INSERT INTO orders (order_id, customer_email, total_amount, estimated_ready, estimated_delivery) 
           VALUES (?, ?, ?, ?, ?)""",
        (order_id, customer_email, total_amount, estimated_ready.isoformat(), estimated_delivery.isoformat())
    )
    
    # Create order items
    for item in items:
        cursor.execute(
            "INSERT INTO order_items (order_id, pizza, size, quantity, price) VALUES (?, ?, ?, ?, ?)",
            (order_id, item['pizza'], item['size'], item['quantity'], item.get('price', 0))
        )
    
    conn.commit()
    conn.close()
    
    return order_id

def get_order(order_id: str):
    """Get order by ID with all items"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    # Get main order
    order = conn.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,)).fetchone()
    if not order:
        conn.close()
        return None
    
    # Get order items
    items = conn.execute(
        "SELECT pizza, size, quantity, price FROM order_items WHERE order_id = ?", 
        (order_id,)
    ).fetchall()
    
    conn.close()
    
    return {
        "order_id": order["order_id"],
        "customer_email": order["customer_email"],
        "items": [dict(item) for item in items],
        "total_amount": order["total_amount"],
        "status": order["status"],
        "prep_time": order["prep_time"],
        "created_at": order["created_at"],
        "estimated_ready": order["estimated_ready"],
        "estimated_delivery": order["estimated_delivery"]
    }

def add_menu_item(name: str, price: float, sizes: list, description: str = None):
    """Add new menu item to database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check for duplicate name
    cursor.execute("SELECT COUNT(*) FROM menu WHERE name = ?", (name,))
    if cursor.fetchone()[0] > 0:
        conn.close()
        raise ValueError(f"Menu item with name '{name}' already exists")
    
    # Insert new menu item
    cursor.execute(
        "INSERT INTO menu (name, price, sizes, description) VALUES (?, ?, ?, ?)",
        (name, price, json.dumps(sizes), description)
    )
    
    # Get the created item
    item_id = cursor.lastrowid
    cursor.execute("SELECT * FROM menu WHERE id = ?", (item_id,))
    item = cursor.fetchone()
    
    conn.commit()
    conn.close()
    
    return {
        "id": item[0],
        "name": item[1],
        "price": item[2],
        "sizes": json.loads(item[3]),
        "description": item[4]
    }
