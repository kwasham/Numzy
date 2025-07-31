# src/numzy/mcp/prompt_server.py
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP
mcp = FastMCP("Receipt Audit MCP Server")

@mcp.prompt()
def generate_audit_instructions(rule_description: str, amount_limit: float = 50.0) -> str:
    """Generate audit instructions for receipt auditing."""
    return f"""You are an expense auditor. Apply the following rule: {rule_description}.

    - Flag receipts where the total exceeds {amount_limit}.
    - Provide reasoning for each flag.
    - Output a JSON object with keys: not_travel_related, amount_over_limit,
      math_error, handwritten_x, reasoning, needs_audit.
    - Set needs_audit to true if any individual flag is true.
    """

if __name__ == "__main__":
    # Try running with streamable-http transport
    mcp.run(transport="streamable-http")
