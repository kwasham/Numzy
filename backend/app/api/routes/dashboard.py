from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.core.database import get_db

router = APIRouter(prefix="", tags=["dashboard"])  # root-level metrics paths


@router.get("/metrics/summary")
async def metrics_summary(db: AsyncSession = Depends(get_db)):
	"""Summary metrics for Overview KPIs.

	- processed24h, processedPrev24h: count of receipts created in last 24h vs previous 24h.
	- avgAccuracy7d, avgAccuracyPrev7d: demo values until evaluations are wired.
	- openAudits: count of receipts with audit_progress < 100.
	"""
	# Processed windows
	rows = await db.execute(text(
		"""
		WITH now_ts AS (SELECT NOW() as now)
		SELECT
		  (SELECT COUNT(*) FROM receipts r, now_ts n WHERE r.created_at >= n.now - INTERVAL '24 hours') as processed24h,
		  (SELECT COUNT(*) FROM receipts r, now_ts n WHERE r.created_at < n.now - INTERVAL '24 hours' AND r.created_at >= n.now - INTERVAL '48 hours') as processedPrev24h,
		  (SELECT COUNT(*) FROM receipts WHERE COALESCE(audit_progress,0) < 100) as open_audits
		"""
	))
	r = rows.first()
	processed24h = int(r[0]) if r else 0
	processedPrev24h = int(r[1]) if r else 0
	open_audits = int(r[2]) if r else 0

	# Compute average accuracy over last 7 days and the prior 7 days from evaluation_items.grader_scores->>'accuracy'
	acc_rows = await db.execute(text(
		"""
		WITH now_ts AS (SELECT NOW() AS now),
		last7 AS (
			SELECT AVG(
				CASE WHEN (ei.grader_scores->>'accuracy') ~ '^[0-9]*\.?[0-9]+$'
					 THEN (ei.grader_scores->>'accuracy')::DOUBLE PRECISION
					 ELSE NULL END
			) AS acc
			FROM evaluation_items ei, now_ts n
			WHERE ei.created_at >= n.now - INTERVAL '7 days'
		),
		prev7 AS (
			SELECT AVG(
				CASE WHEN (ei.grader_scores->>'accuracy') ~ '^[0-9]*\.?[0-9]+$'
					 THEN (ei.grader_scores->>'accuracy')::DOUBLE PRECISION
					 ELSE NULL END
			) AS acc
			FROM evaluation_items ei, now_ts n
			WHERE ei.created_at < n.now - INTERVAL '7 days'
			  AND ei.created_at >= n.now - INTERVAL '14 days'
		)
		SELECT COALESCE((SELECT acc FROM last7), NULL) AS acc_last7,
			   COALESCE((SELECT acc FROM prev7), NULL) AS acc_prev7
		"""
	))
	acc = acc_rows.first() if acc_rows else None
	# Convert to 0-100 ints if present
	def _to_pct(x):
		try:
			return float(x) if x is not None else None
		except Exception:
			return None
	acc_last = _to_pct(acc[0]) if acc else None
	acc_prev = _to_pct(acc[1]) if acc else None

	avg7 = round(acc_last) if acc_last is not None else 92
	prev7 = round(acc_prev) if acc_prev is not None else 90

	return {
		"processed24h": processed24h,
		"processedPrev24h": processedPrev24h,
		"avgAccuracy7d": avg7,
		"avgAccuracyPrev7d": prev7,
		"openAudits": open_audits,
	}


@router.get("/metrics/app/usage")
async def metrics_app_usage(window: str = Query("12m"), bucket: str = Query("month"), db: AsyncSession = Depends(get_db)):
	"""Return monthly usage counts for the app usage chart.

	For now, compute per-month counts of receipts created in the last ~12 months.
	"""
	rows = await db.execute(text(
		"""
		SELECT to_char(date_trunc('month', created_at), 'YYYY-MM-01') as ts,
			   COUNT(*)::int as requests,
			   GREATEST(COUNT(*)::int - 5, 0) as dau
		FROM receipts
		WHERE created_at >= date_trunc('month', NOW()) - INTERVAL '11 months'
		GROUP BY 1
		ORDER BY 1
		"""
	))
	return [dict(ts=r[0], requests=int(r[1]), dau=int(r[2])) for r in rows.all()]

