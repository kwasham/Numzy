"""Receipt extraction service using OpenAI Agents.

This service encapsulates the logic required to extract structured
data from receipt images. It uses the OpenAI Agents SDK to run a
vision‑enabled model and return a ``ReceiptDetails`` instance based
on a Pydantic schema. Image preprocessing, encoding and agent
configuration are handled internally. Should extraction fail for
any reason the service returns an empty ``ReceiptDetails`` object
which allows downstream auditing to continue gracefully.

To customise the extraction prompt you can create or override
``PromptTemplate`` entries via the API; otherwise the default
prompt from ``app.utils.prompts`` is used.
"""

from __future__ import annotations

import base64
import logging
import os
import json
from typing import Optional, Any

from fastapi import HTTPException

from app.core.config import settings
from app.models.schemas import ReceiptDetails
from app.utils.prompts import get_default_extraction_prompt
from app.utils.image_processing import preprocess_image


logger = logging.getLogger(__name__)

# Ensure OpenAI API key is available to libraries that read directly from env
_api_key = settings.OPENAI_API_KEY or os.getenv("OPENAI_API_KEY")
if _api_key:
    os.environ.setdefault("OPENAI_API_KEY", _api_key)

# Try to configure the optional Agents SDK if present
HAS_AGENTS = False
try:  # optional dependency
    from agents import set_default_openai_api  # type: ignore
    set_default_openai_api("responses")
    os.environ["OPENAI_AGENTS_DONT_LOG_MODEL_DATA"] = "1"
    HAS_AGENTS = True
except Exception:
    HAS_AGENTS = False


class ExtractionService:
    """Service responsible for extracting structured receipt details.

    Diagnostic logging can be enabled by setting env var EXTRACTION_DEBUG=1.
    """

    def __init__(self) -> None:
        self.model: str = os.getenv("EXTRACTION_MODEL", "gpt-4o-mini")
        self.debug: bool = os.getenv("EXTRACTION_DEBUG", "0").lower() in {"1", "true", "yes"}
        self.agents_available = HAS_AGENTS
        if self.debug:
            logger.info("[extraction:init] model=%s agents_available=%s", self.model, self.agents_available)

    def _image_to_base64(self, data: bytes) -> str:
        """Encode raw image bytes as a base64 string."""
        return base64.b64encode(data).decode("utf-8")

    async def extract(self, file_data: bytes, filename: str, prompt: Optional[str] = None, model: Optional[str] = None) -> ReceiptDetails:
        """Extract receipt details from an image or PDF.

        :param file_data: Raw bytes of the uploaded file
        :param filename: Original filename (used to detect PDF files)
        :param prompt: Custom prompt string to override the default
        :param model: Optional override of the LLM model name
        :returns: ``ReceiptDetails`` object containing extracted fields
        :raises HTTPException: If the file is a PDF with no pages
        """
        # Use override model if provided
        model_name = model or self.model
        # Convert PDFs to images – import lazily to avoid circular deps
        if filename.lower().endswith(".pdf"):
            from app.api.dependencies import process_pdf_to_images  # type: ignore
            images = await process_pdf_to_images(file_data)
            if not images:
                raise HTTPException(status_code=400, detail="PDF has no pages")
            file_data = images[0]
        # Preprocess image (resize, grayscale) to improve OCR results
        processed = preprocess_image(file_data)
        b64 = self._image_to_base64(processed)
        # Build the agent with the default or custom prompt
        instructions = prompt or get_default_extraction_prompt()
        if self.debug:
            logger.info("[extraction] starting extract filename=%s size=%d model=%s", filename, len(file_data), model_name)

        # ------------------------------ Primary path: Agents SDK ------------------------------
        if self.agents_available:
            try:
                from agents import Agent, Runner  # type: ignore
                agent = Agent(
                    name="receipt_extraction_agent",
                    instructions=instructions,
                    model=model_name,
                    output_type=ReceiptDetails,
                )
                messages = [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "input_image",
                                "detail": "auto",
                                "image_url": f"data:image/jpeg;base64,{b64}",
                            },
                        ],
                    },
                    {
                        "role": "user",
                        "content": "Extract the receipt details from this image according to the ReceiptDetails schema.",
                    },
                ]
                result = await Runner.run(agent, messages)
                if self.debug:
                    logger.info("[extraction] Agents SDK succeeded")
                return result.final_output
            except Exception as exc:
                if self.debug:
                    logger.warning("[extraction] Agents SDK failed: %s", exc)
                else:
                    logger.warning(f"Agents SDK path failed ({exc}); falling back to OpenAI Responses API structured extraction")
        else:
            if self.debug:
                logger.info("[extraction] Agents SDK not available; skipping directly to Responses fallback")

        # ------------------------------ Fallback 1: OpenAI Responses API with JSON schema ------------------------------
        try:
            from openai import OpenAI  # type: ignore
            client = OpenAI()

            # Build JSON schema from Pydantic model (simplify nested defs for OpenAI constraints)
            schema: dict[str, Any] = ReceiptDetails.model_json_schema()
            # Ensure top-level name
            if self.debug:
                logger.info("[extraction] attempting Responses API fallback")
            response = client.responses.create(
                model=model_name,
                input=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "input_image", "image_url": f"data:image/jpeg;base64,{b64}"},
                            {"type": "input_text", "text": instructions + "\nReturn ONLY valid JSON matching the schema."},
                        ],
                    }
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "ReceiptDetails",
                        "schema": schema,
                        "strict": True,
                    },
                },
            )

            # Extract JSON text from response
            raw_json_text = ""
            try:  # cope with evolving SDK structure
                # Newer SDKs: response.output is list of blocks
                output_blocks = getattr(response, "output", []) or []  # type: ignore[attr-defined]
                for block in output_blocks:
                    block_content = getattr(block, "content", []) or []
                    for piece in block_content:
                        p_type = getattr(piece, "type", None)
                        if p_type in ("output_text", "text"):
                            raw_json_text += getattr(piece, "text", "")
                        elif p_type == "tool_call" and self.debug:
                            logger.info("[extraction] responses tool_call piece ignored")
                if not raw_json_text:
                    # Some SDK versions expose consolidated output_text
                    raw_json_text = getattr(response, "output_text", "")  # type: ignore[attr-defined]
            except Exception as ie:
                if self.debug:
                    logger.warning("[extraction] responses content traversal error: %s", ie)

            if not raw_json_text:
                if self.debug:
                    logger.warning("[extraction] Responses fallback produced no text; will try Chat Completions fallback")
                else:
                    logger.error("Responses fallback produced no text; trying next fallback")
                raise RuntimeError("empty responses output")

            try:
                data = json.loads(raw_json_text)
            except json.JSONDecodeError as je:
                if self.debug:
                    logger.warning("[extraction] responses JSON decode failed: %s", je)
                raise

            try:
                rd = ReceiptDetails.model_validate(data)
                if self.debug:
                    logger.info("[extraction] Responses fallback succeeded")
                return rd
            except Exception as ve:
                if self.debug:
                    logger.warning("[extraction] responses validation failed: %s", ve)
                raise
        except Exception as exc2:
            if self.debug:
                logger.warning("[extraction] Responses fallback failed: %s", exc2)

        # ------------------------------ Fallback 2: Chat Completions with JSON schema ------------------------------
        try:
            from openai import OpenAI  # type: ignore
            client2 = OpenAI()
            if self.debug:
                logger.info("[extraction] attempting Chat Completions fallback")
            schema = ReceiptDetails.model_json_schema()
            chat_resp = client2.chat.completions.create(
                model=model_name,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "input_image", "image_url": f"data:image/jpeg;base64,{b64}"},
                            {"type": "text", "text": instructions + "\nReturn ONLY JSON that matches the schema."},
                        ],
                    }
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {"name": "ReceiptDetails", "schema": schema, "strict": True},
            })
            json_text = chat_resp.choices[0].message.content  # type: ignore[attr-defined]
            if isinstance(json_text, list):  # some SDK versions return list of parts
                json_text = "".join(getattr(p, "text", "") for p in json_text)
            data2 = json.loads(json_text)
            rd2 = ReceiptDetails.model_validate(data2)
            if self.debug:
                logger.info("[extraction] Chat completions fallback succeeded")
            return rd2
        except Exception as exc3:
            if self.debug:
                logger.error("[extraction] All extraction paths failed: %s", exc3)
            else:
                logger.error(f"All extraction paths failed: {exc3}")
            return ReceiptDetails()