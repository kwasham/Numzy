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
	- avgAccuracy7d, avgAccuracyPrev7d: placeholder values until evaluations are wired.
	- openAudits: count of receipts with audit_progress < 100.
	"""
	# Lightweight, separate queries to avoid heavy table rewrites or long locks.
	processed24h = int(
		(await db.execute(
			text("""
				SELECT COUNT(*)::int
				FROM receipts
				WHERE created_at >= NOW() - INTERVAL '24 hours'
			""")
		)).scalar() or 0
	)
	processedPrev24h = int(
		(await db.execute(
			text("""
				SELECT COUNT(*)::int
				FROM receipts
				WHERE created_at >= NOW() - INTERVAL '48 hours'
				  AND created_at < NOW() - INTERVAL '24 hours'
			""")
		)).scalar() or 0
	)
	open_audits = int(
		(await db.execute(
			text("""
				SELECT COUNT(*)::int
				FROM receipts
				WHERE COALESCE(audit_progress, 0) < 100
			""")
		)).scalar() or 0
	)

	# Placeholder accuracy values until evaluation metrics are available
	avg7 = 92
	prev7 = 90

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


@router.get("/metrics/spend/categories")
async def metrics_spend_categories(
	limit: int = Query(6, ge=1, le=12),
	window_days: int = Query(365, ge=1, le=3650),
	db: AsyncSession = Depends(get_db),
):
	"""Aggregate spend by category from extracted receipt data for dashboard visuals."""
	query = text(
		r"""
		WITH receipt_source AS (
			SELECT
				id,
				created_at,
				extracted_data,
				categories,
				suggested_categories
			FROM receipts
			WHERE extracted_data IS NOT NULL
		),
		receipt_category AS (
			SELECT
				rs.id,
				COALESCE(
					NULLIF(TRIM(manual.elem), ''),
					NULLIF(TRIM(suggested.elem), ''),
					'Uncategorized'
				) AS category
			FROM receipt_source rs
			LEFT JOIN LATERAL (
					SELECT value
					FROM jsonb_array_elements_text(
						CASE
							WHEN jsonb_typeof(COALESCE(rs.categories::jsonb, '[]'::jsonb)) = 'array'
								THEN COALESCE(rs.categories::jsonb, '[]'::jsonb)
							ELSE '[]'::jsonb
						END
					)
				LIMIT 1
			) AS manual(elem) ON TRUE
			LEFT JOIN LATERAL (
					SELECT value
					FROM jsonb_array_elements_text(
						CASE
							WHEN jsonb_typeof(COALESCE(rs.suggested_categories::jsonb, '[]'::jsonb)) = 'array'
								THEN COALESCE(rs.suggested_categories::jsonb, '[]'::jsonb)
							ELSE '[]'::jsonb
						END
					)
				LIMIT 1
			) AS suggested(elem) ON TRUE
		),
		receipt_totals AS (
			SELECT
				COALESCE(rc.category, 'Uncategorized') AS category,
				CASE
					WHEN (rs.extracted_data->>'total') ~ '^-?[0-9]+(\.[0-9]+)?$' THEN (rs.extracted_data->>'total')::numeric
					WHEN regexp_replace(rs.extracted_data->>'total', '[^0-9.-]', '', 'g') ~ '^-?[0-9]+(\.[0-9]+)?$'
						THEN regexp_replace(rs.extracted_data->>'total', '[^0-9.-]', '', 'g')::numeric
					ELSE NULL
				END AS amount,
				rs.created_at
			FROM receipt_source rs
			LEFT JOIN receipt_category rc ON rc.id = rs.id
		),
		filtered AS (
			SELECT category, amount
			FROM receipt_totals
			WHERE amount IS NOT NULL
			  AND amount > 0
			  AND created_at >= NOW() - (:window_days || ' days')::interval
		),
		aggregated AS (
			SELECT category,
			       SUM(amount) AS total,
			       COUNT(*)::int AS contribution_count
			FROM filtered
			GROUP BY category
		)
		SELECT category,
		       total,
		       contribution_count,
		       SUM(total) OVER () AS grand_total
		FROM aggregated
		ORDER BY total DESC, category ASC
		LIMIT :limit
		"""
	)
	params = {"limit": limit, "window_days": window_days}
	rows = (await db.execute(query, params)).fetchall()
	total_amount = sum(float(row.total or 0) for row in rows)
	if total_amount <= 0 and window_days < 3650:
		params["window_days"] = 3650
		rows = (await db.execute(query, params)).fetchall()
		total_amount = sum(float(row.total or 0) for row in rows)
	items = [
		{
			"name": row.category,
			"amount": float(row.total or 0),
			"count": int(row.contribution_count or 0),
		}
		for row in rows
	]
	return {"total": total_amount, "items": items}

