# receipt_processing_api/app/mcp/prompt_server.py
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP with host setting
mcp = FastMCP(
    "Receipt Audit MCP Server",
    host="0.0.0.0",  # Important: Listen on all interfaces for Docker
    port=8000
)

@mcp.prompt()
def generate_audit_instructions(rule_description: str, amount_limit: float = 50.0) -> str:
    """
    Generate audit instructions based on a natural-language rule and amount threshold.
    Returns a plain string; the SDK wraps this in a streaming response.
    """
    return (
        f"You are an expense auditor. Apply the following rule: {rule_description}.\n"
        f"- Flag receipts where the total exceeds {amount_limit}.\n"
        "- Provide reasoning for each flag.\n"
        "- Output a JSON object with keys: not_travel_related, amount_over_limit,\n"
        "  math_error, handwritten_x, reasoning, needs_audit.\n"
        "- Set needs_audit to true if any individual flag is true."
    )

if __name__ == "__main__":
    # Run with streamable-http transport
    mcp.run(transport="streamable-http")
