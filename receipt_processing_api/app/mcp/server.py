from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Prompt Server")

@mcp.prompt()
def generate_audit_instructions(rule_description: str, amount_limit: float = 50.0) -> str:
    return f"""You are an expense auditor. Apply this rule: {rule_description}.
    Instructions:
    - Flag receipts where total > {amount_limit}.
    - Provide reasoning for each flag and output a JSON AuditDecision.
    Response schema: not_travel_related, amount_over_limit, math_error, handwritten_x, reasoning, needs_audit.
    Set `needs_audit` true if any individual flag is true."""

@mcp.get("/health")
async def health_check():
    return {"status": "healthy", "service": "MCP Server"}

if __name__ == "__main__":
    mcp.run(transport="streamable-http")