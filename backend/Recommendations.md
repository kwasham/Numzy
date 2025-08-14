# Recommendations for Numzy Repository

# Review of Numzy Repository and Recommendations

## Existing Architecture

The **Numzy** repository is a modular FastAPI backend for receipt extraction, auditing, evaluation and cost analysis.  Key services include:

### Extraction Service

* `ExtractionService` uses the OpenAI Agents SDK to parse receipt images. It preprocesses an image or first page of a PDF, encodes it to base64 and builds an `Agent` configured with a default or custom prompt. The agent’s output type is the `ReceiptDetails` Pydantic model. It calls `Runner.run` with a message containing the image and the extraction instruction; if extraction fails it returns an empty `ReceiptDetails` so that auditing can still proceed.

### Audit Service and Rule Engine

* `AuditService` loads all active rules for a user or organisation, converts them into simple dictionaries and passes them to `evaluate_rules`.
* The **rule engine** supports threshold, keyword, category and time‑based rules, returning flags and reasoning; other rule types (pattern, ML, Python, LLM) are stubbed and always return `False`.
* If no rules exist, the audit service builds a default prompt with few‑shot examples and uses an OpenAI agent to return a structured `AuditDecision`. Otherwise it maps the flags produced by the rule engine to standard audit fields (not travel‑related, amount over limit, math error and handwritten X) and returns a structured decision.

### Evaluation and Cost Analysis

* `EvaluationService` orchestrates extraction and audit across a set of receipts, storing predicted and reference results and computing basic metrics such as correct merchant/total/item count and audit accuracy.
* `CostService` estimates financial impact from evaluation results, given false positive/negative rates and per‑receipt costs.

### Prompt and Rule Management

* The API exposes CRUD routes for prompt templates and audit rules. Users can save custom extraction or audit prompts, update or delete them.
* Audit rules are stored with a name, type (`threshold`, `keyword`, `category`, `time`, `pattern`, `ml`, `python`, `llm`) and JSON configuration; free‑plan users have limitations enforced when creating rules.

### Architecture Documentation

* `Structure.md` proposes a clean directory layout and outlines domain models (User, Organisation, Receipt, AuditRule, PromptTemplate, Evaluation, CostAnalysis) and services. It also includes technology recommendations for backend and frontend development.

## Recommendations

1. **Integrate a Modular Prompt‑Server (MCP) for Dynamic Audit Rules**.  Build a new `mcp` module using openai‑agents’ `FastMCP` server to expose parameterised prompts over HTTP. When a user describes an audit rule in plain language, call the MCP server to generate a formatted audit prompt and save it as a `PromptTemplate`. The `AuditService` can then fetch these prompts when deterministic rules are insufficient. This allows non‑technical users to create reusable audit prompts via natural language.

2. **Extend the Rule Engine Beyond Stubs**.  Implement the currently stubbed rule types:

   * **Pattern rules** should accept regular expressions and flag receipts when a description or category matches.
   * **Python rules** can evaluate safe, sandboxed expressions with access to receipt fields; restrict the environment to avoid arbitrary code execution.
   * **ML rules** should integrate a classifier or anomaly detector and trigger based on probability thresholds.
   * **LLM rules** can call an LLM with a rule‑specific prompt (potentially generated via MCP) and interpret the response as a boolean flag.

3. **Natural Language Rule Creation Workflow**.  Provide an endpoint that accepts a rule description like “Flag receipts over \$100 on weekends.” Use an LLM (via the Agents SDK or the MCP server) to parse this description into one or more structured rule configurations (e.g., threshold and time rules) and return both the generated `AuditRule` objects and a human‑readable explanation. If the rule cannot be expressed deterministically, fallback to generating a custom audit prompt via MCP.

4. **Enhance Evaluation Metrics and Reporting**.  Expand the evaluation metrics to include precision, recall and F1 scores for each audit flag, and provide per‑rule true positive/false positive rates. Show confusion matrices and charts in the dashboard to help users fine‑tune rules.

5. **User Experience and Dashboard Improvements**.  Build an interactive Next.js 15 dashboard using Tailwind CSS v4 and Shadcn UI. Offer forms for structured rule creation and natural language rule entry, display evaluation and cost‑analysis results, and allow model selection. Implement glassmorphism panels and use Tremor for charts, as suggested in `Structure.md`.

6. **Performance, Observability & Security**.

   * *Performance*: optimise image preprocessing and consider streaming large PDF conversions; tune task queue concurrency.
   * *Observability*: add structured logging and metrics around LLM calls and rule evaluations; use OpenTelemetry for tracing.
   * *Security*: store API keys securely; sandbox user‑provided Python rules; sanitise LLM inputs and enforce output schemas.

7. **Testing & Continuous Integration**.  Add unit tests for rule evaluation and services, integration tests for extraction and audit, and API tests for route permissions. Use GitHub Actions to run tests and static analysis on each pull request.

## Example Integration: OpenAI Agents MCP Prompt Server

Below is a minimal example showing how to integrate an **MCP prompt server** into the Numzy codebase. The server exposes a prompt function that generates audit instructions from a natural‑language description and optional parameters. Clients can query the server for available prompts and retrieve the customised prompt to use when calling the audit agent.

```python
# file: numzy/mcp/server.py
from fastapi import FastAPI
from agents import Agent
from openai_agents.mcp import FastMCP, prompt  # adjust import based on SDK version

# Instantiate FastAPI and MCP
app = FastAPI()
mcp = FastMCP()

@prompt(name="generate_audit_prompt")
def generate_audit_prompt(rule_description: str, max_total: float = 50.0) -> str:
    """Return a formatted audit prompt based on user-supplied criteria.

    Parameters:
      rule_description: Natural language description of the audit rule (e.g., "flag receipts over $100 on weekends").
      max_total: Optional default threshold for the amount_over_limit rule.

    This function constructs a prompt instructing the agent to audit a receipt according to the user’s rule.  You could
    include default examples or use few-shot examples from the existing prompt library.
    """
    base_instructions = (
        "You are an expense auditor. Apply the following rule when deciding if a receipt needs an audit:\\n"
        f"Rule: {rule_description}. "
        "Check the receipt details and return a JSON AuditDecision with these fields:\\n"
        "not_travel_related, amount_over_limit, math_error, handwritten_x, reasoning, needs_audit."
        "\\nSet needs_audit to true if any individual flag is true."
    )
    # Insert dynamic threshold logic into the instructions
    threshold_clause = f" Treat any total greater than {max_total} as over the limit."
    return base_instructions + threshold_clause

# Mount the MCP routes under /mcp
app.mount("/mcp", mcp)

# Optional: Root endpoint for health checks
@app.get("/")
def health_check():
    return {"status": "ok"}
```

### Using the MCP server in the audit service

In your `AuditService`, when a user has provided a natural‑language rule, fetch the prompt from the MCP server before constructing the agent:

```python
import httpx
from app.models.schemas import AuditDecision

class AuditService:
    ...
    async def _get_custom_audit_prompt(self, rule_description: str) -> str:
        """Call the MCP server to generate an audit prompt from a rule description."""
        async with httpx.AsyncClient(base_url="http://mcp-service:8000") as client:
            # list available prompts or directly call by name
            response = await client.get(
                "/mcp/prompts/generate_audit_prompt",
                params={"rule_description": rule_description}
            )
            response.raise_for_status()
            # Response shape depends on the MCP implementation; adjust accordingly
            return response.json().get("prompt")

    async def audit(self, details: ReceiptDetails, user_id: int, organisation_id: Optional[int] = None) -> AuditDecision:
        # Load deterministic rules as before ...
        if not rule_dicts and user_custom_rule_description:
            # Fetch a prompt for the custom rule via MCP
            prompt_text = await self._get_custom_audit_prompt(user_custom_rule_description)
            agent = Agent(
                name="receipt_audit_agent_custom",
                instructions=prompt_text,
                model=self.model,
                output_type=AuditDecision,
            )
            input_message = f"Audit this receipt data:\\n\\n{details.model_dump_json(indent=2)}"
            result = await Runner.run(agent, input_message)
            return result.final_output
        # Otherwise, fall back to deterministic or default audit logic
```

This example uses a separate service (`mcp-service`) to host the MCP server. In a development environment you could run it alongside the API via Docker Compose. In production, you might expose it internally and cache generated prompts in the `PromptTemplate` table for future use. By adopting this pattern, **Numzy** gains dynamic, natural‑language driven prompt generation while keeping deterministic rules and explicit prompt templates for reproducibility.
