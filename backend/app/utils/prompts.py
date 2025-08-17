"""Default prompt templates for extraction and auditing.

This module contains helper functions that return default prompts
used by the extraction and audit services. You can override these
prompts by creating custom prompt templates via the API. Keeping
prompts in a central location makes it easier to iterate on their
content and ensure consistency across the application.
"""

from __future__ import annotations

from textwrap import dedent


def get_default_extraction_prompt() -> str:
    """Return a default prompt used for extracting receipt details.

    The prompt instructs the model to parse a receipt image into
    structured fields defined by the ``ReceiptDetails`` schema. It
    emphasises that the output must be JSON serialisable and match
    the schema exactly. You can customise this prompt by creating
    a ``PromptTemplate`` of type ``extraction``.
    """
    return dedent(
        """
        You are an assistant specialised in parsing retail receipts. You
        will be given an image of a receipt and must extract the
        merchant name, location, timestamp, line items, subtotal, tax,
        total and any handwritten notes. Use the following JSON schema
        for the output:

                ReceiptDetails: {
          merchant: string | null,
          location: {
            city: string | null,
            state: string | null,
            zipcode: string | null,
          },
          time: ISO8601 datetime string | null,
          items: [
            {
              description: string | null,
              product_code: string | null,
              category: string | null,
              item_price: string | null,
              sale_price: string | null,
              quantity: string | null,
              total: string | null,
            },
          ],
          subtotal: string | null,
          tax: string | null,
          total: string | null,
          handwritten_notes: [string],
                    payment_method: {
                        type: string | null,        // e.g., card, cash, apple_pay
                        brand: string | null,       // e.g., Visa, Mastercard, Amex
                        last4: string | null,       // last 4 digits if printed
                        cardholder: string | null,  // name on card if present
                    },
        }

        Only provide fields you can infer from the receipt. If a field
        is missing then use null or an empty list as appropriate. Do
        not hallucinate or attempt to derive values that are not
        clearly present.
        """
    ).strip()


def get_default_audit_prompt() -> str:
    """Return a default audit prompt to be formatted with examples.

    This prompt explains the audit rules and asks the model to
    determine whether a receipt should be audited. It is designed to
    be formatted with a string of few-shot examples before being
    passed to the model. See ``get_audit_examples_string`` for
    generating those examples.
    """
    return dedent(
        """
        You are an expense auditor. The following examples show how to
        apply business rules to decide whether a receipt requires
        auditing. Each example consists of the input receipt data
        followed by the audit decision JSON. Use these examples as
        guidance for determining the audit flags and writing a clear
        explanation.

        {examples}

        Now audit the given receipt. Respond with a JSON object
        matching the following schema:

        AuditDecision: {{
          not_travel_related: boolean,
          amount_over_limit: boolean,
          math_error: boolean,
          handwritten_x: boolean,
          reasoning: string,
          needs_audit: boolean,
        }}

        Set ``needs_audit`` to true if any of the individual flags is
        true. Explain the rationale behind each flag in the reasoning.
        """
    ).strip()


def get_audit_examples_string() -> str:
    """Return a string of few‑shot examples for the audit prompt.

    These examples mirror those used in the original receipt
    inspection notebook. They illustrate how to set audit flags and
    compose reasoning. If you add or remove examples here be sure to
    update the corresponding expected outputs in the tests.
    """
    # Hard‑coded examples for clarity; in a production system you
    # could fetch examples from the database or a config file.
    examples = []
    # Example 1
    examples.append(
        (
            '{\n  "merchant": "WESTERN SIERRA NURSERY",\n  "location": {"city": "Oakhurst", "state": "CA", "zipcode": "93644"},\n  "time": "2024-09-27T12:33:38",\n  "items": [{"description": "Plantskydd Repellent RTU 1 Liter", "product_code": null, "category": "Garden/Pest Control", "item_price": "24.99", "sale_price": null, "quantity": "1", "total": "24.99"}],\n  "subtotal": "24.99",\n  "tax": "1.94",\n  "total": "26.93",\n  "handwritten_notes": []\n}',
            '{"not_travel_related": true, "amount_over_limit": false, "math_error": false, "handwritten_x": false, "reasoning": "1. The merchant is a plant nursery so the purchase is not travel-related. 2. The total is under $50. 3. The line items sum correctly. 4. There are no handwritten notes.", "needs_audit": true}'
        )
    )
    # Example 2
    examples.append(
        (
            '{\n  "merchant": "Flying J #616",\n  "location": {"city": "Frazier Park", "state": "CA", "zipcode": null},\n  "time": "2024-10-01T13:23:00",\n  "items": [{"description": "Unleaded", "product_code": null, "category": "Fuel", "item_price": "4.459", "sale_price": null, "quantity": "11.076", "total": "49.39"}],\n  "subtotal": "49.39",\n  "tax": null,\n  "total": "49.39",\n  "handwritten_notes": ["yos -> home sequoia", "236660"]\n}',
            '{"not_travel_related": false, "amount_over_limit": false, "math_error": false, "handwritten_x": false, "reasoning": "1. Fuel is travel-related. 2. Total is under $50. 3. Calculations match the total. 4. No X in handwritten notes.", "needs_audit": false}'
        )
    )
    # Example 3
    examples.append(
        (
            '{\n  "merchant": "O\'Reilly Auto Parts",\n  "location": {"city": "Sylmar", "state": "CA", "zipcode": "91342"},\n  "time": "2024-04-26T08:43:11",\n  "items": [{"description": "VAL 5W-20", "product_code": null, "category": "Auto", "item_price": "12.28", "sale_price": null, "quantity": "1", "total": "12.28"}],\n  "subtotal": "12.28",\n  "tax": "1.07",\n  "total": "13.35",\n  "handwritten_notes": ["vista -> yos"]\n}',
            '{"not_travel_related": false, "amount_over_limit": false, "math_error": false, "handwritten_x": false, "reasoning": "1. Engine oil may be required for travel. 2. Total is under $50. 3. Calculations match. 4. No X in notes.", "needs_audit": false}'
        )
    )
    # Format as the prompt expects: input followed by output separated by blank lines
    lines = []
    for inp, out in examples:
        lines.append(f"\n\n{inp}\n\n{out}\n\n")
    return "".join(lines)