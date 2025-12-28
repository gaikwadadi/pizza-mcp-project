#!/usr/bin/env python3
"""Extract OpenAPI specification from FastAPI backend"""

import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.main import app

def extract_openapi():
    """Extract OpenAPI spec and save to file"""
    openapi_spec = app.openapi()
    
    # Create specs directory if it doesn't exist
    specs_dir = project_root / "specs"
    specs_dir.mkdir(exist_ok=True)
    
    # Save OpenAPI spec
    spec_file = specs_dir / "pizza_openapi.json"
    with open(spec_file, "w") as f:
        json.dump(openapi_spec, f, indent=2)
    
    print(f"OpenAPI specification saved to: {spec_file}")
    print(f"Endpoints found: {len(openapi_spec.get('paths', {}))}")
    
    # Print summary
    for path, methods in openapi_spec.get('paths', {}).items():
        for method in methods.keys():
            print(f"  {method.upper()} {path}")

if __name__ == "__main__":
    extract_openapi()
