import asyncio
from agents.mcp import MCPServerStreamableHttp

async def main():
    # Connect to MCP server running in Docker (port 8001)
    async with MCPServerStreamableHttp(
        name="Audit Prompt Client",
        params={"url": "http://localhost:8001"},
    ) as server:
        # Call the prompt endpoint
        result = await server.get_prompt(
            "generate_audit_instructions",
            {
                "rule_description": "Flag receipts over $100",
                "amount_limit": 100
            }
        )
        print("Prompt result:", result.messages[0].content)

if __name__ == "__main__":
    asyncio.run(main())