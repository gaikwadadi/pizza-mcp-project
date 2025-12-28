from typing import Dict, Any, List
from .utils import to_snake_case, sanitize_description

def convert_path_to_tool_name(path: str, method: str) -> str:
    """Convert OpenAPI path and method to MCP tool name"""
    # Remove slashes and braces, convert to snake_case
    clean_path = path.replace('/', '_').replace('{', '').replace('}', '')
    if clean_path.startswith('_'):
        clean_path = clean_path[1:]
    
    # Add method prefix
    method_prefix = method.lower()
    if method_prefix == 'post':
        method_prefix = 'create'
    elif method_prefix == 'put' or method_prefix == 'patch':
        method_prefix = 'update'
    elif method_prefix == 'delete':
        method_prefix = 'delete'
    
    if clean_path:
        return f"{method_prefix}_{to_snake_case(clean_path)}"
    else:
        return method_prefix

def convert_schema_to_input_schema(openapi_schema: Dict[str, Any]) -> Dict[str, Any]:
    """Map OpenAPI schema to JSON Schema for MCP"""
    if not openapi_schema:
        return {"type": "object", "properties": {}, "required": []}
    
    # Handle $ref
    if "$ref" in openapi_schema:
        # For now, return basic object - will be resolved by caller
        return {"type": "object", "properties": {}, "required": []}
    
    schema_type = openapi_schema.get("type", "object")
    
    if schema_type == "object":
        properties = {}
        for prop_name, prop_spec in openapi_schema.get("properties", {}).items():
            properties[prop_name] = convert_schema_to_input_schema(prop_spec)
        
        return {
            "type": "object",
            "properties": properties,
            "required": openapi_schema.get("required", [])
        }
    
    elif schema_type == "array":
        items = openapi_schema.get("items", {})
        return {
            "type": "array",
            "items": convert_schema_to_input_schema(items)
        }
    
    else:
        # Primitive types
        result = {"type": schema_type}
        if "description" in openapi_schema:
            result["description"] = sanitize_description(openapi_schema["description"])
        if "default" in openapi_schema:
            result["default"] = openapi_schema["default"]
        if "title" in openapi_schema:
            result["title"] = openapi_schema["title"]
        return result

def extract_parameters(endpoint: Dict[str, Any], components: Dict[str, Any]) -> Dict[str, Any]:
    """Combine path params, query params, request body into unified inputSchema"""
    schema = {
        "type": "object",
        "properties": {},
        "required": []
    }
    
    # Handle path and query parameters
    for param in endpoint.get("parameters", []):
        param_name = param["name"]
        param_schema = param.get("schema", {"type": "string"})
        
        schema["properties"][param_name] = convert_schema_to_input_schema(param_schema)
        
        if param.get("required", False):
            schema["required"].append(param_name)
        
        # Add description
        if "description" in param:
            schema["properties"][param_name]["description"] = sanitize_description(param["description"])
    
    # Handle request body
    request_body = endpoint.get("requestBody")
    if request_body and "content" in request_body:
        content = request_body["content"]
        if "application/json" in content:
            json_schema = content["application/json"]["schema"]
            
            # Resolve $ref if present
            if "$ref" in json_schema:
                ref_name = json_schema["$ref"].split("/")[-1]
                if "schemas" in components and ref_name in components["schemas"]:
                    resolved_schema = components["schemas"][ref_name]
                    
                    # Merge properties from resolved schema
                    for prop_name, prop_spec in resolved_schema.get("properties", {}).items():
                        schema["properties"][prop_name] = convert_schema_to_input_schema(prop_spec)
                    
                    # Merge required fields
                    for req_field in resolved_schema.get("required", []):
                        if req_field not in schema["required"]:
                            schema["required"].append(req_field)
            else:
                # Direct schema
                body_schema = convert_schema_to_input_schema(json_schema)
                if body_schema.get("type") == "object":
                    schema["properties"].update(body_schema.get("properties", {}))
                    schema["required"].extend(body_schema.get("required", []))
    
    return schema

def create_mcp_tool_definition(endpoint: Dict[str, Any], components: Dict[str, Any]) -> Dict[str, Any]:
    """Generate MCP Tool definition from endpoint"""
    tool_name = convert_path_to_tool_name(endpoint["path"], endpoint["method"])
    input_schema = extract_parameters(endpoint, components)
    
    description = endpoint.get("summary", "")
    if not description:
        description = f"{endpoint['method']} {endpoint['path']}"
    
    return {
        "name": tool_name,
        "description": sanitize_description(description),
        "inputSchema": input_schema,
        "endpoint": {
            "path": endpoint["path"],
            "method": endpoint["method"]
        }
    }
