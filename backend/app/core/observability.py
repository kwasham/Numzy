"""Observability helpers (Sentry init & common scrubbing).

Centralises Sentry initialisation for API and worker so configuration
does not drift. Keeps initialisation a no-op if the SDK or DSN are
missing.
"""

from __future__ import annotations

from typing import Any, Dict

from app.core.config import settings

try:  # Optional import
	import sentry_sdk  # type: ignore
	from sentry_sdk.integrations.fastapi import FastApiIntegration  # type: ignore
	from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration  # type: ignore
	_SENTRY_AVAILABLE = True
except Exception:  # pragma: no cover
	_SENTRY_AVAILABLE = False


def _before_send(event: Dict[str, Any], hint: Dict[str, Any] | None = None):  # type: ignore[override]
	"""Scrub obvious PII / secrets before sending to Sentry.

	- Drop Authorization & Cookie headers
	- Remove request data/body (keep method + URL)
	- Optionally collapse large contexts
	"""
	try:
		req = event.get("request") or {}
		headers = req.get("headers") or {}
		for k in list(headers.keys()):
			lk = k.lower()
			if lk in ("authorization", "cookie", "set-cookie", "x-api-key"):
				headers.pop(k, None)
		if "data" in req:
			# Avoid leaking raw bodies
			req.pop("data", None)
		event["request"] = req
	except Exception:  # best effort
		pass
	return event


def init_sentry(service: str) -> bool:
	"""Initialise Sentry once for a given process.

	Returns True if Sentry was initialised; False otherwise.
	"""
	if not (_SENTRY_AVAILABLE and settings.SENTRY_DSN):  # pragma: no cover - simple guard
		return False
	if getattr(init_sentry, "_done", False):  # prevent duplicate init in same process
		return True
	sentry_sdk.init(
		dsn=settings.SENTRY_DSN,
		integrations=[FastApiIntegration(), SqlalchemyIntegration()],
		traces_sample_rate=float(settings.SENTRY_TRACES_SAMPLE_RATE or 0),
		profiles_sample_rate=float(settings.SENTRY_PROFILES_SAMPLE_RATE or 0),
		environment=settings.ENVIRONMENT,
		release=settings.SENTRY_RELEASE,
		before_send=_before_send,
	)
	sentry_sdk.set_tag("service", service)
	init_sentry._done = True  # type: ignore[attr-defined]
	return True


__all__ = ["init_sentry"]
