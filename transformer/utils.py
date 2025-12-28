import re
from typing import Dict, Any

def to_snake_case(text: str) -> str:
    """Convert text to snake_case"""
    # Replace hyphens and spaces with underscores
    text = re.sub(r'[-\s]+', '_', text)
    # Insert underscore before uppercase letters
    text = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', text)
    return text.lower()

def to_camel_case(text: str) -> str:
    """Convert text to camelCase"""
    components = text.split('_')
    return components[0] + ''.join(word.capitalize() for word in components[1:])

def validate_openapi_version(spec: Dict[str, Any]) -> bool:
    """Check if OpenAPI version is 3.x"""
    version = spec.get("openapi", "")
    return version.startswith("3.")

def sanitize_description(text: str) -> str:
    """Clean descriptions for code generation"""
    if not text:
        return ""
    # Remove newlines and extra spaces
    text = re.sub(r'\s+', ' ', text.strip())
    # Escape quotes
    text = text.replace('"', '\\"')
    return text
