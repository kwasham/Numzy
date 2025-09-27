// Centralized receipt caches to enable optimistic hydration across list + modal
// Stored shape: id -> { data: <receiptLike>, ts: number, partial: boolean }

// Increase TTL for non-terminal receipts to 10 minutes. Active statuses will be refreshed via SSE.
export const DETAIL_TTL_MS = 600_000;
export const TERMINAL_STATUSES = new Set(["processed", "failed", "completed", "canceled", "rejected"]);

export const detailCache = new Map(); // receiptId (number|string) -> { data, ts, partial }
export const previewCache = new Map(); // receiptId (number|string) -> { src, ts, loaded?: boolean, objectUrl?: boolean }

// Track recent thumbnail fetch attempts to suppress spammy repeat 204s when an image is unavailable (or auth suppressed).
// id -> lastAttemptTs
const thumbAttemptMap = new Map();
// Default cooldown (ms) between attempts for the same receipt when previous attempt returned no usable image.
export const THUMB_ATTEMPT_COOLDOWN_MS = 60_000; // 60s (tune as needed)

export function shouldAttemptThumb(id, cooldownMs = THUMB_ATTEMPT_COOLDOWN_MS) {
	if (id == null) return false;
	const now = Date.now();
	const last = thumbAttemptMap.get(id) ?? thumbAttemptMap.get(String(id));
	if (last && now - last < cooldownMs) return false;
	thumbAttemptMap.set(id, now);
	thumbAttemptMap.set(String(id), now);
	return true;
}

export function markThumbFailure(id) {
	if (id == null) return;
	const now = Date.now();
	thumbAttemptMap.set(id, now);
	thumbAttemptMap.set(String(id), now);
}

export function resetThumbAttempt(id) {
	if (id == null) return;
	thumbAttemptMap.delete(id);
	thumbAttemptMap.delete(String(id));
}

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
	// If we already have full extracted_data, treat as full detail; else mark partial.
	const full = row.extracted_data && typeof row.extracted_data === "object";
	const shape = {
		id: row.id,
		status: row.status,
		created_at: row.created_at,
		filename: row.filename || row.original_filename || null,
		extracted_data: row.extracted_data || null,
		audit_decision: row.audit_decision || null,
	};
	setDual(detailCache, row.id, { data: shape, ts: Date.now(), partial: !full });
}

// Public helper to set full detail data (used by modal)
export function setFullDetail(id, data) {
	setDual(detailCache, id, { data, ts: Date.now(), partial: false });
}

// Public helper to set preview src
export function setPreview(id, src, loaded = false, objectUrl = false) {
	setDual(previewCache, id, { src, ts: Date.now(), loaded, objectUrl });
}

// Convenience: fetch a URL, store as object URL (fully downloaded image) for instant display.
// Caller responsible for ensuring same-origin or CORS that allows blob usage.
export async function fetchAndSetPreviewObjectUrl(id, url) {
	try {
		const res = await fetch(url, { cache: "no-store" });
		if (!res.ok) return null;
		const ct = res.headers.get("content-type") || "";
		if (!ct.startsWith("image")) return null;
		const blob = await res.blob();
		const objectUrl = URL.createObjectURL(blob);
		setPreview(id, objectUrl, true, true);
		return objectUrl;
	} catch {
		return null;
	}
}

export function revokePreviewObjectUrl(id) {
	const entry = previewCache.get(id) || previewCache.get(String(id));
	if (entry && entry.objectUrl && entry.src && typeof entry.src === "string" && entry.src.startsWith("blob:")) {
		try {
			URL.revokeObjectURL(entry.src);
		} catch {
			/* ignore */
		}
		previewCache.delete(id);
		previewCache.delete(String(id));
	}
}

// Remove a receipt (detail + preview cache) and revoke any object URL.
export function deleteReceiptCache(id) {
	if (id == null) return;
	detailCache.delete(id);
	detailCache.delete(String(id));
	const prev = previewCache.get(id) || previewCache.get(String(id));
	if (prev && prev.objectUrl && typeof prev.src === "string" && prev.src.startsWith("blob:")) {
		try {
			URL.revokeObjectURL(prev.src);
		} catch {
			/* ignore */
		}
	}
	previewCache.delete(id);
	previewCache.delete(String(id));
}

export function isFresh(entry) {
	if (!entry) return false;
	const status = (entry.data?.status || "").toLowerCase();
	if (TERMINAL_STATUSES.has(status)) return true;
	return Date.now() - entry.ts < DETAIL_TTL_MS;
}
