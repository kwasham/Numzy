"""Minimal MCP server for testing receipt extraction."""

from fastapi import FastAPI
from typing import Dict, Any, List, Optional
from mcp.server.fastmcp import FastMCP
import uvicorn

app = FastAPI()
mcp = FastMCP()

# In-memory storage for testing
user_contexts = {}

@mcp.prompt(name="extract_receipt")
async def extract_receipt(
    image_base64: str,
    user_id: int,
    filename: str,
    custom_hints: Optional[str] = None
) -> Dict[str, str]:
    """Generate extraction prompt."""
    prompt_text = """You are an expert receipt parser. Extract all information from this receipt.

Return a JSON object with:
{
    "merchant_name": "string",
    "total_amount": number,
    "date": "YYYY-MM-DD",
    "items": [{"description": "string", "quantity": number, "price": number}],
    "payment_method": "string",
    "tax_amount": number,
    "tip_amount": number
}

Guidelines:
- Be precise with numbers
- Use today's date if unclear
- Extract all line items
- Include payment method details"""
    
    if custom_hints:
        prompt_text += f"\n\nAdditional hints: {custom_hints}"
    
    return {"prompt": prompt_text}

@mcp.prompt(name="audit_receipt")
async def audit_receipt(
    receipt_data: Dict[str, Any],
    audit_rules: List[Dict[str, Any]],
    user_id: int,
    strictness: str = "medium"
) -> Dict[str, str]:
    """Generate audit prompt."""
    prompt_text = f"""You are an expense auditor. Audit this receipt:

{receipt_data}

Strictness level: {strictness}

Check for:
1. Amounts over $50
2. Mathematical errors
3. Unusual patterns
4. Policy violations

Return JSON:
{{
    "needs_audit": boolean,
    "amount_over_limit": boolean,
    "math_error": boolean,
    "risk_score": 0-100,
    "reasoning": "explanation",
    "recommendations": ["suggestions"]
}}"""
    
    return {"prompt": prompt_text}

@mcp.resource(uri="user_preferences/{user_id}")
async def get_user_preferences(user_id: int) -> Dict[str, Any]:
    """Get user preferences."""
    return {
        "preferred_categories": ["Food & Dining", "Travel", "Office"],
        "common_merchants": ["Starbucks", "Amazon", "Uber"],
        "audit_strictness": "medium",
        "extraction_hints": {}
    }

@mcp.resource(uri="audit_rules/{user_id}")
async def get_audit_rules(user_id: int) -> List[Dict[str, Any]]:
    """Get audit rules."""
    return [
        {
            "id": 1,
            "name": "High amount threshold",
            "type": "threshold",
            "config": {"threshold": 50.0},
            "description": "Flag receipts over $50"
        },
        {
            "id": 2,
            "name": "Weekend purchases",
            "type": "time",
            "config": {"days": ["saturday", "sunday"]},
            "description": "Flag weekend expenses"
        }
    ]

@mcp.tool(name="validate_receipt_math")
async def validate_receipt_math(receipt_data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate receipt mathematics."""
    items = receipt_data.get("items", [])
    subtotal = sum(item.get("price", 0) * item.get("quantity", 1) for item in items)
    tax = receipt_data.get("tax_amount", 0)
    tip = receipt_data.get("tip_amount", 0)
    expected = subtotal + tax + tip
    actual = receipt_data.get("total_amount", 0)
    
    return {
        "subtotal": subtotal,
        "expected_total": expected,
        "actual_total": actual,
        "math_error": abs(expected - actual) > 0.01,
        "discrepancy": expected - actual
    }

# Mount MCP
app.mount("/mcp", mcp)

@app.get("/")
async def health():
    return {"status": "healthy", "service": "MCP Test Server"}

if __name__ == "__main__":
    print("Starting MCP server on http://localhost:8001")
    print("Press Ctrl+C to stop")
    uvicorn.run(app, host="0.0.0.0", port=8001)