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
        self.model: str = os.getenv("EXTRACTION_MODEL", "gpt-5")
        self.debug: bool = os.getenv("EXTRACTION_DEBUG", "0").lower() in {"1", "true", "yes"}
        self.agents_available = HAS_AGENTS
        if self.debug:
            logger.info("[extraction:init] model=%s agents_available=%s", self.model, self.agents_available)

    def _image_to_base64(self, data: bytes) -> str:
        """Encode raw image bytes as a base64 string."""
        return base64.b64encode(data).decode("utf-8")

    async def extract(self, file_data: bytes, filename: str, prompt: Optional[str] = None, model: Optional[str] = None) -> ReceiptDetails:
        """Extract receipt details from an image or PDF with fallback + retry heuristics.

        Strategy:
        1. Normalise / preprocess image (PDF -> first page image, EXIF orientation already handled upstream if any).
        2. Attempt extraction with primary model (``EXTRACTION_MODEL`` or provided override).
        3. If result appears *minimal* (only merchant or empty) automatically retry a small cascade of fallback
           models (configurable via ``EXTRACTION_MODEL_FALLBACKS`` env var or a sensible default).
        4. Return the first non-minimal result; otherwise return the last attempt.

        A result is considered minimal when it lacks items AND lacks total/subtotal/tax while merchant alone may be present.
        """
        # Resolve primary + fallback models early
        primary_model = (model or self.model or "gpt-4o-mini").strip()
        # Some environments may still use placeholder / deprecated names; map obvious placeholders.
        placeholder_map = {
            "gpt-5": "gpt-4o-mini",  # speculative placeholder -> widely available lightweight model
            "gpt5": "gpt-4o-mini",
        }
        primary_model = placeholder_map.get(primary_model.lower(), primary_model)
        fb_env = os.getenv("EXTRACTION_MODEL_FALLBACKS", "gpt-4o-mini")
        fallback_models = [m.strip() for m in fb_env.split(",") if m.strip()]
        # Ensure primary is first and unique ordering
        cascade: list[str] = []
        seen = set()
        for m in [primary_model] + fallback_models:
            key = m.lower()
            if key in seen:
                continue
            cascade.append(m)
            seen.add(key)

        def _is_minimal(details: ReceiptDetails) -> bool:
            try:
                if details.items and len(details.items) > 0:
                    return False
                rich_fields = [details.total, details.subtotal, details.tax, details.shipping, details.receiving]
                if any(f for f in rich_fields if f not in (None, "")):
                    return False
                # Merchant alone or completely empty qualifies as minimal
                return True
            except Exception:
                return True
        # Convert PDFs to images – try shared helper, else inline fallback
        if filename.lower().endswith(".pdf"):
            images: list[bytes] = []
            try:
                try:  # Prefer shared helper if present
                    from app.api.dependencies import process_pdf_to_images as _proc  # type: ignore
                except Exception:
                    _proc = None  # type: ignore
                if _proc:
                    try:
                        if self.debug:
                            logger.info("[extraction][pdf] using shared process_pdf_to_images helper")
                        images = await _proc(file_data)  # type: ignore[arg-type]
                    except Exception:
                        images = []
                # Inline fallback using PyMuPDF directly if helper absent or returned nothing
                if not images:
                    try:  # best effort
                        import fitz  # type: ignore
                        if self.debug:
                            logger.info("[extraction][pdf] inline PyMuPDF fallback engaged (helper missing or empty)")
                        doc = fitz.open(stream=file_data, filetype="pdf")
                        if doc.page_count > 0:
                            page = doc.load_page(0)
                            pix = page.get_pixmap()
                            images = [pix.tobytes("png")]
                        doc.close()
                    except Exception:
                        images = []
            except Exception:
                images = []
            if not images:
                raise HTTPException(status_code=400, detail="PDF has no pages or could not be rendered")
            file_data = images[0]
        # Preprocess image (resize, grayscale, orientation) to improve OCR results
        processed = preprocess_image(file_data)
        b64 = self._image_to_base64(processed)
        # Build the agent with the default or custom prompt
        instructions = prompt or get_default_extraction_prompt()
        if self.debug:
            logger.info("[extraction] starting extract filename=%s size=%d cascade=%s", filename, len(file_data), cascade)

        last_details: ReceiptDetails | None = None
        last_error: Exception | None = None

        # Inner function performing a single attempt (keeps original logic) ------------------
        async def _attempt(model_name: str) -> ReceiptDetails:
            if self.debug:
                logger.info("[extraction][attempt] model=%s", model_name)
            # Stash original self.model when calling; some SDK paths reference self.model implicitly
            # but we explicitly pass model_name to downstream calls where possible.
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
                        logger.info("[extraction][attempt] Agents SDK succeeded model=%s", model_name)
                    return result.final_output
                except Exception as exc:
                    if self.debug:
                        logger.warning("[extraction][attempt] Agents SDK failed model=%s err=%s", model_name, exc)
                    # continue to fallback logic below
            else:
                if self.debug:
                    logger.info("[extraction][attempt] Agents SDK unavailable; using Responses/Chat path")

            # ------------------------------ Fallback 1: OpenAI Responses API ------------------------------
            try:
                from openai import OpenAI  # type: ignore
                client = OpenAI()
                schema: dict[str, Any] = ReceiptDetails.model_json_schema()
                if self.debug:
                    logger.info("[extraction][attempt] responses api model=%s", model_name)
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
                        "json_schema": {"name": "ReceiptDetails", "schema": schema, "strict": True},
                    },
                )
                raw_json_text = ""
                try:
                    output_blocks = getattr(response, "output", []) or []  # type: ignore[attr-defined]
                    for block in output_blocks:
                        for piece in getattr(block, "content", []) or []:
                            p_type = getattr(piece, "type", None)
                            if p_type in ("output_text", "text"):
                                raw_json_text += getattr(piece, "text", "")
                    if not raw_json_text:
                        raw_json_text = getattr(response, "output_text", "")  # type: ignore[attr-defined]
                except Exception as inner_exc:  # pragma: no cover - diagnostic only
                    if self.debug:
                        logger.warning("[extraction][attempt] responses traversal error model=%s err=%s", model_name, inner_exc)
                if not raw_json_text:
                    raise RuntimeError("empty responses output")
                data = json.loads(raw_json_text)
                rd = ReceiptDetails.model_validate(data)
                if self.debug:
                    logger.info("[extraction][attempt] responses api succeeded model=%s", model_name)
                return rd
            except Exception as exc2:
                if self.debug:
                    logger.warning("[extraction][attempt] responses api failed model=%s err=%s", model_name, exc2)
            # ------------------------------ Fallback 2: Chat Completions ------------------------------
            try:
                from openai import OpenAI  # type: ignore
                client2 = OpenAI()
                if self.debug:
                    logger.info("[extraction][attempt] chat completions model=%s", model_name)
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
                if isinstance(json_text, list):
                    json_text = "".join(getattr(p, "text", "") for p in json_text)
                data2 = json.loads(json_text)
                rd2 = ReceiptDetails.model_validate(data2)
                if self.debug:
                    logger.info("[extraction][attempt] chat completions succeeded model=%s", model_name)
                return rd2
            except Exception as exc3:
                if self.debug:
                    logger.warning("[extraction][attempt] chat completions failed model=%s err=%s", model_name, exc3)
            # All attempts failed for this model
            return ReceiptDetails()

        # Iterate cascade
        for mdl in cascade:
            try:
                details = await _attempt(mdl)
                last_details = details
                if not _is_minimal(details):
                    if self.debug:
                        logger.info("[extraction] accepted model=%s (non-minimal)", mdl)
                    return details
                else:
                    if self.debug:
                        logger.warning("[extraction] minimal result model=%s; trying next fallback", mdl)
            except Exception as attempt_exc:  # pragma: no cover - defensive
                last_error = attempt_exc
                if self.debug:
                    logger.warning("[extraction] attempt failed model=%s err=%s", mdl, attempt_exc)
                continue

        # All attempts yielded minimal or failed; return last (possibly empty)
        if self.debug and last_details is not None:
            logger.warning("[extraction] returning minimal result after cascade models=%s last_error=%s", cascade, last_error)
        return last_details or ReceiptDetails()
        # End extract