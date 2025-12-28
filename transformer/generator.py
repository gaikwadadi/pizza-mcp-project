import os
import json
from datetime import datetime
from typing import List, Dict, Any

def generate_mcp_server_code(tools: List[Dict[str, Any]], base_url: str, openapi_spec_file: str) -> str:
    """Use template to create Python file"""
    
    # Read template
    template_path = os.path.join(os.path.dirname(__file__), "templates", "mcp_server_template.py")
    with open(template_path, 'r') as f:
        template = f.read()
    
    # Generate tool definitions for @server.list_tools()
    tool_definitions = _generate_tool_definitions(tools)
    
    # Generate tool handlers for @server.call_tool()
    tool_handlers = _generate_tool_handlers(tools)
    
    # Replace template placeholders
    code = template.format(
        openapi_spec_file=openapi_spec_file,
        timestamp=datetime.now().isoformat(),
        base_url=base_url,
        tool_definitions=tool_definitions,
        tool_handlers=tool_handlers
    )
    
    return code

def _generate_tool_definitions(tools: List[Dict[str, Any]]) -> str:
    """Generate @server.list_tools() handler"""
    tool_items = []
    
    for tool in tools:
        schema_str = json.dumps(tool["inputSchema"], indent=12)
        # Indent the schema properly
        schema_lines = schema_str.split('\n')
        indented_schema = '\n'.join('        ' + line if line.strip() else line for line in schema_lines)
        
        tool_def = f'''Tool(
            name="{tool["name"]}",
            description="{tool["description"]}",
            inputSchema={indented_schema}
        )'''
        tool_items.append(tool_def)
    
    tools_list = ',\n        '.join(tool_items)
    
    return f'''@server.list_tools()
async def handle_list_tools() -> List[Tool]:
    return [
        {tools_list}
    ]'''

def _generate_tool_handlers(tools: List[Dict[str, Any]]) -> str:
    """Generate @server.call_tool() handler and individual tool functions"""
    
    # Generate main call handler
    conditions = []
    for tool in tools:
        conditions.append(f'    if name == "{tool["name"]}":\n        return await {tool["name"]}_handler(arguments)')
    
    call_handler = f'''@server.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
{chr(10).join(conditions)}
    
    raise ValueError(f"Unknown tool: {{name}}")'''
    
    # Generate individual tool handlers
    individual_handlers = []
    for tool in tools:
        http_call = _generate_http_call(tool)
        
        handler = f'''async def {tool["name"]}_handler(arguments: Dict[str, Any]) -> List[TextContent]:
    async with httpx.AsyncClient() as client:
{http_call}
        return [TextContent(type="text", text=json.dumps(response.json()))]'''
        
        individual_handlers.append(handler)
    
    return call_handler + '\n\n' + '\n\n'.join(individual_handlers)

def _generate_http_call(tool: Dict[str, Any]) -> str:
    """Generate HTTP client call for tool"""
    method = tool["endpoint"]["method"].lower()
    path = tool["endpoint"]["path"]
    
    if method == "get":
        if "{" in path:  # Path parameter
            # Extract parameter name
            param_name = path.split("{")[1].split("}")[0]
            clean_path = path.replace("{" + param_name + "}", "{arguments['" + param_name + "']}")
            return f'        url = f"{{BASE_URL}}{clean_path}"\n        response = await client.get(url)'
        else:
            return f'        response = await client.get(f"{{BASE_URL}}{path}")'
    
    elif method == "post":
        return f'        response = await client.post(f"{{BASE_URL}}{path}", json=arguments)'
    
    elif method in ["put", "patch"]:
        return f'        response = await client.{method}(f"{{BASE_URL}}{path}", json=arguments)'
    
    elif method == "delete":
        if "{" in path:
            param_name = path.split("{")[1].split("}")[0]
            clean_path = path.replace("{" + param_name + "}", "{arguments['" + param_name + "']}")
            return f'        url = f"{{BASE_URL}}{clean_path}"\n        response = await client.delete(url)'
        else:
            return f'        response = await client.delete(f"{{BASE_URL}}{path}")'
    
    return f'        response = await client.request("{method.upper()}", f"{{BASE_URL}}{path}", json=arguments)'

def save_generated_server(code: str, output_path: str) -> None:
    """Write to file, make executable, add header comments"""
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Write code to file
    with open(output_path, 'w') as f:
        f.write(code)
    
    # Make executable
    os.chmod(output_path, 0o755)
