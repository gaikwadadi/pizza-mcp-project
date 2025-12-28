#!/usr/bin/env python3

import argparse
import sys
import logging
from .parser import parse_openapi, extract_endpoints
from .mapper import create_mcp_tool_definition
from .generator import generate_mcp_server_code, save_generated_server

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def main():
    """CLI interface for OpenAPI to MCP transformer"""
    parser = argparse.ArgumentParser(
        description="Transform OpenAPI specification to MCP server",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--input", 
        required=True, 
        help="Path to OpenAPI specification file (JSON or YAML)"
    )
    parser.add_argument(
        "--output", 
        default="generated/pizza_mcp_server.py", 
        help="Output path for generated MCP server (default: generated/pizza_mcp_server.py)"
    )
    parser.add_argument(
        "--base-url", 
        default="http://localhost:8000", 
        help="Backend API base URL (default: http://localhost:8000)"
    )
    
    args = parser.parse_args()
    
    try:
        # Phase 1: Parse OpenAPI specification
        logger.info(f"Parsing OpenAPI specification: {args.input}")
        spec = parse_openapi(args.input)
        logger.info(f"Successfully parsed OpenAPI {spec.get('openapi', 'unknown')} specification")
        
        # Phase 2: Extract endpoints
        logger.info("Extracting endpoints from specification")
        endpoints = extract_endpoints(spec)
        logger.info(f"Found {len(endpoints)} endpoints")
        
        # Phase 3: Map to MCP tools
        logger.info("Converting endpoints to MCP tools")
        tools = []
        components = spec.get("components", {})
        
        for endpoint in endpoints:
            try:
                tool = create_mcp_tool_definition(endpoint, components)
                tools.append(tool)
                logger.info(f"  ✓ {endpoint['method']} {endpoint['path']} → {tool['name']}")
            except Exception as e:
                logger.error(f"  ✗ Failed to convert {endpoint['method']} {endpoint['path']}: {e}")
                continue
        
        if not tools:
            logger.error("No tools were successfully generated")
            sys.exit(1)
        
        logger.info(f"Successfully generated {len(tools)} MCP tools")
        
        # Phase 4: Generate MCP server code
        logger.info("Generating MCP server code using template")
        server_code = generate_mcp_server_code(tools, args.base_url, args.input)
        
        # Phase 5: Save generated server
        logger.info(f"Saving generated MCP server to: {args.output}")
        save_generated_server(server_code, args.output)
        
        logger.info("✅ OpenAPI to MCP transformation completed successfully!")
        logger.info(f"Generated MCP server: {args.output}")
        logger.info(f"Tools available: {', '.join(tool['name'] for tool in tools)}")
        
    except Exception as e:
        logger.error(f"❌ Transformation failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
