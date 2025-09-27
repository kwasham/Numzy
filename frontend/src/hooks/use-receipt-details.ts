// Custom hook extracting receipt detail + preview logic from the modal without adding a new data library.
// It leverages the shared in-memory caches and SSE events already present in the app.

import * as React from "react";
import { useAuth } from "@clerk/nextjs";

import {
	detailCache,
	isFresh,
	previewCache,
	setFullDetail,
	setPreview,
} from "@/components/dashboard/receipts/receipt-cache";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Retry helper (mirrors modal implementation)
async function fetchSignedUrlWithRetry(
	path: string,
	headers: Record<string, string> | undefined,
	attempts = [300, 800, 1500]
) {
	for (let i = 0; i <= attempts.length; i++) {
		try {
			const res = await fetch(`${API_URL}${path}`, { headers });
			if (res.ok) {
				const { url } = await res.json();
				return `${API_URL}${url}`;
			}
			if (res.status === 409 && i < attempts.length) {
				await new Promise((r) => setTimeout(r, attempts[i]));
				continue;
			}
			return null;
		} catch {
			if (i < attempts.length) {
				await new Promise((r) => setTimeout(r, attempts[i]));
				continue;
			}
			return null;
		}
	}
	return null;
}

// Narrow shape we rely on (extend as needed).
export interface ReceiptLike {
	id: number | string;
	status?: string;
	created_at?: string;
	filename?: string | null;
	extracted_data?: unknown;
	audit_decision?: unknown;
	[k: string]: unknown;
}

export interface UseReceiptDetailsOptions {
	open: boolean;
	receiptId: number | string | null;
	providedReceipt?: ReceiptLike | null; // partial or full receipt passed from parent (list)
	prefetchedPreview?: string | null; // optional already-fetched preview URL
}

export interface UseReceiptDetailsResult {
	receipt: ReceiptLike | null;
	loading: boolean;
	refreshing: boolean;
	error: string | null;
	previewSrc: string | null;
	previewLoading: boolean;
	previewRefreshing: boolean;
	downloadUrl: string | null; // original/processed file URL even if no image thumbnail
	manualRefreshPreview: () => void;
}

export function useReceiptDetails({
	open,
	receiptId,
	providedReceipt,
	prefetchedPreview,
}: UseReceiptDetailsOptions): UseReceiptDetailsResult {
	const { getToken } = useAuth();

	const [detailState, setDetailState] = React.useState<{
		data: ReceiptLike | null;
		loading: boolean;
		refreshing: boolean;
		error: string | null;
	}>({
		data: null,
		loading: false,
		refreshing: false,
		error: null,
	});
	const [previewState, setPreviewState] = React.useState<{
		src: string | null;
		loading: boolean;
		refreshing: boolean;
		downloadUrl: string | null;
	}>(() => ({
		src: prefetchedPreview || null,
		loading: !prefetchedPreview,
		refreshing: false,
		downloadUrl: null,
	}));

	// Track last receipt id to reset preview cleanly when switching quickly.
	const lastPreviewIdRef = React.useRef<string | number | null>(null);
	// Reload nonce to force refetch when user manually refreshes or status changes
	const [previewReloadNonce, setPreviewReloadNonce] = React.useState(0);
	// Throttle timestamp for preview fetch starts (avoid redundant rapid re-runs)
	const lastPreviewFetchRef = React.useRef<number>(0);
	React.useEffect(() => {
		if (!open) return;
		if (lastPreviewIdRef.current !== receiptId) {
			lastPreviewIdRef.current = receiptId;
			setPreviewState({
				src: prefetchedPreview || null,
				loading: !prefetchedPreview,
				refreshing: false,
				downloadUrl: null,
			});
		}
	}, [open, receiptId, prefetchedPreview]);

	const detailAbortRef = React.useRef<AbortController | null>(null);
	const previewAbortRef = React.useRef<AbortController | null>(null);

	// Detail fetch effect
	React.useEffect(() => {
		if (!open || !receiptId) return;
		// Provided receipt short-circuits network
		if (providedReceipt) {
			setDetailState({ data: providedReceipt, loading: false, refreshing: false, error: null });
			setFullDetail(providedReceipt.id, providedReceipt);
			return; // skip normal fetch
		}

		if (detailAbortRef.current) detailAbortRef.current.abort();
		const controller = new AbortController();
		detailAbortRef.current = controller;
		const cached = detailCache.get(receiptId) || detailCache.get(String(receiptId));
		const fresh = isFresh(cached);
		if (cached) {
			setDetailState({ data: cached.data, loading: false, refreshing: !fresh, error: null });
			if (fresh && !cached.partial) return () => controller.abort();
		} else {
			setDetailState({ data: null, loading: true, refreshing: false, error: null });
		}
		(async () => {
			try {
				let token: string | null = null;
				try {
					token = (await getToken?.()) || null;
				} catch {
					/* ignore */
				}
				const url = token
					? `/api/receipts/${encodeURIComponent(receiptId)}?token=${encodeURIComponent(token)}`
					: `/api/receipts/${encodeURIComponent(receiptId)}`;
				const res = await fetch(url, { cache: "no-store", signal: controller.signal });
				if (!res.ok) throw new Error(res.status === 404 ? "Receipt not found" : `Failed (${res.status})`);
				const data = await res.json();
				if (controller.signal.aborted) return;
				setFullDetail(receiptId, data);
				setDetailState({ data, loading: false, refreshing: false, error: null });
			} catch (error) {
				if (controller.signal.aborted) return;
				const message = error instanceof Error ? error.message : "Failed to load";
				setDetailState((prev) => ({ ...prev, loading: false, refreshing: false, error: message }));
			}
		})();
		return () => {
			controller.abort();
		};
	}, [open, receiptId, providedReceipt, getToken]);

	// Preview fetch effect (adds short polling & fallback). Re-runs on previewReloadNonce.
	React.useEffect(() => {
		if (!open || !receiptId) return;
		const effectStartedAt = Date.now();
		let forcedTimeoutFired = false;

		// Abort any in-flight preview request
		if (previewAbortRef.current) previewAbortRef.current.abort();
		const controller = new AbortController();
		previewAbortRef.current = controller;

		// Read cache first to decide UI state before any throttling
		const cached = previewCache.get(receiptId) || previewCache.get(String(receiptId));
		if (cached && cached.src) {
			setPreviewState({ src: cached.src, loading: false, refreshing: true, downloadUrl: cached.downloadUrl || null });
		} else if (prefetchedPreview && !cached) {
			setPreviewState({ src: prefetchedPreview, loading: false, refreshing: true, downloadUrl: null });
		} else if (!cached) {
			setPreviewState({ src: null, loading: true, refreshing: false, downloadUrl: null });
		}

		// Throttle only if we already have something to show (cached/prefetched). If there's no src yet,
		// do NOT return early; otherwise the UI could be stuck in loading without a hard-timeout.
		const now = Date.now();
		const isThrottledWindow = now - lastPreviewFetchRef.current < 400 && previewReloadNonce === 0;
		const haveSrcAlready = Boolean((cached && cached.src) || prefetchedPreview);
		if (isThrottledWindow && haveSrcAlready) {
			return () => controller.abort();
		}
		lastPreviewFetchRef.current = now;

		(async () => {
			try {
				let token: string | null = null;
				try {
					token = (await getToken?.()) || null;
				} catch {
					/* ignore */
				}
				const auth = token ? { Authorization: `Bearer ${token}` } : undefined;
				const thumb = `/api/receipts/${encodeURIComponent(receiptId)}/thumb`;
				let chosen: string | null = null;
				let chosenDownload: string | null = null; // non-image fallback

				// Fire download URL request in parallel to provide an immediate fallback UI
				const dlPromise = (async () => {
					try {
						const dl = await fetchSignedUrlWithRetry(
							`/receipts/${encodeURIComponent(receiptId)}/download_url`,
							auth,
							[400, 900, 1800]
						);
						if (controller.signal.aborted) return null;
						if (dl) {
							const absolute = dl.startsWith("http") ? dl : `${API_URL}${dl}`;
							// Immediately expose as download fallback so UI can swap out of skeleton
							chosenDownload = absolute;
							setPreviewState((p) => (p.downloadUrl ? p : { ...p, downloadUrl: absolute }));
							return absolute;
						}
					} catch {
						/* ignore */
					}
					return null;
				})();

				const attemptDelays = [0, 400, 900, 1800]; // faster progressive backoff (total ~3.1s)
				for (let i = 0; i < attemptDelays.length && !chosen; i++) {
					if (attemptDelays[i] > 0) await new Promise((r) => setTimeout(r, attemptDelays[i]));
					if (controller.signal.aborted) return;
					try {
						const r = await fetch(thumb, { cache: "no-store", signal: controller.signal });
						if (controller.signal.aborted) return;
						if (r.status === 401 || r.status === 403) break; // stop attempts
						const ct = r.headers.get("content-type") || "";
						const placeholderReason = r.headers.get("x-thumb-fallback");
						const stage = r.headers.get("x-thumb-stage");
						if (process.env.NEXT_PUBLIC_DEBUG_RECEIPTS === "true") {
							console.debug("[receipt-preview] attempt", {
								receiptId,
								attempt: i,
								status: r.status,
								contentType: ct,
								placeholder: Boolean(placeholderReason),
								placeholderReason,
								stage,
							});
						}
						// Accept any image so we can show PDF placeholders or generated thumbs immediately.
						if (r.ok && ct.startsWith("image")) {
							chosen = thumb; // use route directly; cache-bust via query later
							break;
						}
						// If thumbnail still not ready and we already have a download URL, bail out early after second try.
						if (chosenDownload && i >= 1) {
							chosen = chosenDownload;
							break;
						}
						// Otherwise continue to next attempt
					} catch {
						// Network error: if we have a download URL, use it immediately.
						if (chosenDownload) {
							chosen = chosenDownload;
							break;
						}
					}
				}

				// Ensure download URL promise resolves so chosenDownload is populated when available
				if (!chosenDownload) {
					try {
						await dlPromise;
					} catch {
						/* ignore */
					}
				}

				if (!chosen && chosenDownload) {
					// Try to load as image regardless of extension; onerror handler will fall back to download
					chosen = chosenDownload;
				}

				if (controller.signal.aborted) return;
				if (!chosen) {
					// No image preview available; record download URL if present
					setPreviewState((p) => ({ ...p, loading: false, refreshing: false, downloadUrl: chosenDownload }));
					// Schedule another attempt if still open & no downloadUrl & under retry cap
					if (!chosenDownload && previewReloadNonce < 6) {
						setTimeout(() => {
							if (!controller.signal.aborted) setPreviewReloadNonce((n) => n + 1);
						}, 5000);
					}
					return;
				}

				// Immediately set the src so the UI switches from the big skeleton to the image container
				setPreviewState((p) => ({
					...p,
					src: chosen!,
					loading: false,
					refreshing: false,
					downloadUrl: chosenDownload,
				}));

				const img = new Image();
				img.addEventListener("load", () => {
					if (controller.signal.aborted) return;
					setPreview(receiptId, chosen!, true, false);
					if (process.env.NEXT_PUBLIC_DEBUG_RECEIPTS === "true") {
						console.debug("[receipt-preview] loaded", { receiptId, chosen, placeholder: !chosen || !!chosenDownload });
					}
					// Ensure state reflects any late downloadUrl and confirm src
					setPreviewState({ src: chosen, loading: false, refreshing: false, downloadUrl: chosenDownload });
				});
				img.addEventListener("error", () => {
					if (controller.signal.aborted) return;
					setPreviewState((p) => ({ ...p, loading: false, refreshing: false, downloadUrl: chosenDownload }));
				});
				img.src = chosen.includes("?") ? `${chosen}&cb=${Date.now()}` : `${chosen}?cb=${Date.now()}`;
			} catch {
				if (!controller.signal.aborted)
					setPreviewState((p) => ({ ...p, loading: false, refreshing: false, downloadUrl: p.downloadUrl || null }));
			}
		})();

		// Hard stop guard: after 3s, if still loading with no src, flip to fallback (prevents endless skeleton)
		const _hardTimeout = setTimeout(() => {
			if (controller.signal.aborted) return;
			if (forcedTimeoutFired) return;
			forcedTimeoutFired = true;
			setPreviewState((p) => {
				if (!p.loading || p.src) return p; // already resolved
				return { ...p, loading: false, refreshing: false };
			});
			if (process.env.NEXT_PUBLIC_DEBUG_RECEIPTS === "true") {
				console.debug("[receipt-preview] hard-timeout fallback", { receiptId, sinceMs: Date.now() - effectStartedAt });
			}
		}, 3000);
		return () => {
			controller.abort();
			clearTimeout(_hardTimeout);
		};
	}, [open, receiptId, getToken, prefetchedPreview, previewReloadNonce]);

	// SSE update effect (status updates + trigger preview retry when processed/completed & no preview yet)
	React.useEffect(() => {
		if (!open || !receiptId) return;
		type ReceiptUpdateEvent = { receipt_id: number | string; status?: string };
		function onUpdate(ev: Event) {
			const detail = (ev as CustomEvent).detail as ReceiptUpdateEvent | undefined;
			if (!detail || detail.receipt_id !== receiptId) return;
			setDetailState((prev) => {
				if (!prev.data) return prev;
				const next = { ...prev.data } as ReceiptLike;
				if (typeof detail.status === "string") next.status = detail.status.toLowerCase();
				detailCache.set(receiptId, { data: next, ts: Date.now(), partial: false });
				if (["processed", "completed"].includes((next.status as string) || "")) {
					const cachedPrev = previewCache.get(receiptId) || previewCache.get(String(receiptId));
					if (!cachedPrev?.src) setPreviewReloadNonce((n) => n + 1);
				}
				return { ...prev, data: next };
			});
		}
		globalThis.addEventListener("receipt:update", onUpdate);
		return () => globalThis.removeEventListener("receipt:update", onUpdate);
	}, [open, receiptId]);

	const manualRefreshPreview = React.useCallback(() => {
		if (!receiptId) return;
		previewCache.delete(receiptId);
		setPreviewState({ src: null, loading: true, refreshing: false, downloadUrl: null });
		setPreviewReloadNonce((n) => n + 1);
	}, [receiptId]);

	// Provide preview with stable cache-busting param like original component
	const previewSrc = React.useMemo(() => {
		if (!previewState.src) return null;
		// If this is an object URL (already fully downloaded) return as is.
		if (previewState.src.startsWith("blob:")) return previewState.src;
		// Avoid layering multiple cache-bust params if already added in prefetch phase.
		const base = previewState.src;
		if (/([?&])rid=/.test(base)) return base; // already has rid
		const join = base.includes("?") ? "&" : "?";
		return `${base}${join}rid=${encodeURIComponent(String(receiptId || ""))}`;
	}, [previewState.src, receiptId]);

	return {
		receipt: detailState.data,
		loading: detailState.loading,
		refreshing: detailState.refreshing,
		error: detailState.error,
		previewSrc,
		previewLoading: previewState.loading,
		previewRefreshing: previewState.refreshing,
		downloadUrl: previewState.downloadUrl,
		manualRefreshPreview,
	};
}
