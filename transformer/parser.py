import json
import yaml
from typing import Dict, Any, List
from .utils import validate_openapi_version

def parse_openapi(file_path: str) -> Dict[str, Any]:
    """Read JSON/YAML file and validate OpenAPI 3.x format"""
    try:
        with open(file_path, 'r') as f:
            if file_path.endswith('.yaml') or file_path.endswith('.yml'):
                spec = yaml.safe_load(f)
            else:
                spec = json.load(f)
        
        if not validate_openapi_version(spec):
            raise ValueError(f"Invalid OpenAPI version. Expected 3.x, got {spec.get('openapi', 'unknown')}")
        
        return spec
    
    except Exception as e:
        raise ValueError(f"Failed to parse OpenAPI spec: {e}")

def extract_endpoints(spec: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Parse each path and method, extract endpoint details"""
    endpoints = []
    
    paths = spec.get("paths", {})
    for path, methods in paths.items():
        for method, method_spec in methods.items():
            if method.lower() in ['get', 'post', 'put', 'patch', 'delete']:
                endpoint = {
                    "path": path,
                    "method": method.upper(),
                    "summary": method_spec.get("summary", ""),
                    "description": method_spec.get("description", ""),
                    "parameters": method_spec.get("parameters", []),
                    "requestBody": method_spec.get("requestBody"),
                    "responses": method_spec.get("responses", {})
                }
                endpoints.append(endpoint)
    
    return endpoints
