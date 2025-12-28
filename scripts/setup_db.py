#!/usr/bin/env python3
"""Initialize the pizza database"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.database import init_db

if __name__ == "__main__":
    print("Initializing pizza database...")
    init_db()
    print("Database initialized successfully!")
