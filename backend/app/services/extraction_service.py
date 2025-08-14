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
from typing import Optional

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
try:  # optional dependency
    from agents import set_default_openai_api  # type: ignore
    # Ensure the Agents SDK uses the Responses API rather than chat completions
    set_default_openai_api("responses")
    # Disable logging of model data to avoid leaking receipt content
    os.environ["OPENAI_AGENTS_DONT_LOG_MODEL_DATA"] = "1"
except Exception:  # pragma: no cover - non-fatal
    pass


class ExtractionService:
    """Service responsible for extracting structured receipt details."""

    def __init__(self) -> None:
        # Configure the default model used for extraction
        self.model: str = "gpt-4o-mini"

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
        try:
            # Import optional Agents SDK lazily
            from agents import Agent, Runner  # type: ignore

            agent = Agent(
                name="receipt_extraction_agent",
                instructions=instructions,
                model=model_name,
                output_type=ReceiptDetails,
            )
            # Compose messages: first message contains the image, second the task
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
            return result.final_output
        except Exception as exc:
            logger.error(f"Extraction error or Agents SDK missing: {exc}")
            # Return an empty details object on failure
            return ReceiptDetails()