// Centralized receipt caches to enable optimistic hydration across list + modal
// Stored shape: id -> { data: <receiptLike>, ts: number, partial: boolean }

// Increase TTL for non-terminal receipts to 10 minutes. Active statuses will be refreshed via SSE.
export const DETAIL_TTL_MS = 600_000;
export const TERMINAL_STATUSES = new Set(["processed", "failed", "completed", "canceled", "rejected"]);

export const detailCache = new Map(); // receiptId (number|string) -> { data, ts, partial }
export const previewCache = new Map(); // receiptId (number|string) -> { src, ts }

// Internal helpers to set under both numeric + string keys (avoids first-open cache miss due to type mismatch)
function setDual(map, id, value) {
	if (id == null) return;
	const num = typeof id === "number" ? id : Number(id);
	if (Number.isFinite(num)) {
		map.set(num, value);
		map.set(String(num), value);
	} else {
		map.set(String(id), value);
	}
}

export function primePartialReceipt(row) {
	if (!row || row.id == null) return;
	const existing = detailCache.get(row.id) || detailCache.get(String(row.id));
	// If we already have a non-partial (full) and it's fresh, keep it.
	if (existing && !existing.partial) return;
	// Build minimal shape expected by modal
	const minimal = {
		id: row.id,
		status: row.status,
		created_at: row.created_at,
		filename: row.filename || row.original_filename || null,
		extracted_data: row.extracted_data || null,
		audit_decision: row.audit_decision || null,
	};
	setDual(detailCache, row.id, { data: minimal, ts: Date.now(), partial: true });
}

// Public helper to set full detail data (used by modal)
export function setFullDetail(id, data) {
	setDual(detailCache, id, { data, ts: Date.now(), partial: false });
}

// Public helper to set preview src
export function setPreview(id, src) {
	setDual(previewCache, id, { src, ts: Date.now() });
}

export function isFresh(entry) {
	if (!entry) return false;
	const status = (entry.data?.status || "").toLowerCase();
	if (TERMINAL_STATUSES.has(status)) return true;
	return Date.now() - entry.ts < DETAIL_TTL_MS;
}
