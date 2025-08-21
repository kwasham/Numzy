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


from typing import Any, Dict, Optional


def sentry_set_tags(tags: Dict[str, Any]) -> None:
	"""Best-effort: set tags on current Sentry scope (strings only)."""
	try:
		if not (_SENTRY_AVAILABLE and settings.SENTRY_DSN):
			return
		import sentry_sdk  # type: ignore
		with sentry_sdk.configure_scope() as scope:  # type: ignore
			for k, v in (tags or {}).items():
				# Avoid PII; coerce to short strings
				scope.set_tag(str(k), str(v)[:128] if v is not None else "")
	except Exception:
		return


def sentry_breadcrumb(category: str, message: str, level: str = "info", data: Optional[Dict[str, Any]] = None) -> None:
	"""Best-effort: add a breadcrumb for important lifecycle steps."""
	try:
		if not (_SENTRY_AVAILABLE and settings.SENTRY_DSN):
			return
		import sentry_sdk  # type: ignore
		sentry_sdk.add_breadcrumb(  # type: ignore
			category=category,
			message=message,
			level=level,
			data=data or {},
		)
	except Exception:
		return


def sentry_metric_inc(name: str, value: int = 1, tags: Optional[Dict[str, Any]] = None) -> None:
	"""Best-effort: increment a metric using Sentry Metrics if available.

	Falls back to no-op when metrics are unavailable.
	"""
	try:
		if not (_SENTRY_AVAILABLE and settings.SENTRY_DSN):
			return
		from sentry_sdk import metrics  # type: ignore
		# Sentry Python SDK expects numeric value and optional tags
		# Coerce tag values to short strings to avoid PII/large payloads
		safe_tags = {str(k): str(v)[:64] for k, v in (tags or {}).items()}
		metrics.increment(name, value=value, tags=safe_tags)  # type: ignore
	except Exception:
		return


__all__ = ["init_sentry", "sentry_set_tags", "sentry_breadcrumb", "sentry_metric_inc"]
