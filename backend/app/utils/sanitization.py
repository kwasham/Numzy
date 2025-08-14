"""
Input sanitization utilities for API payloads.
Provides functions to clean and validate string inputs.
"""

import re
from typing import Optional

def sanitize_string(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    # Remove leading/trailing whitespace and dangerous characters
    value = value.strip()
    # Remove control characters
    value = re.sub(r'[\x00-\x1F\x7F]', '', value)
    # Escape HTML
    value = value.replace('<', '&lt;').replace('>', '&gt;')
    return value

# Usage: In Pydantic validators or directly in route handlers
# Example:
# @validator('name')
# def clean_name(cls, v):
#     return sanitize_string(v)
