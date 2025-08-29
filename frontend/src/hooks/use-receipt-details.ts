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
}

export interface UseReceiptDetailsResult {
	receipt: ReceiptLike | null;
	loading: boolean;
	refreshing: boolean;
	error: string | null;
	previewSrc: string | null;
	previewLoading: boolean;
	previewRefreshing: boolean;
	manualRefreshPreview: () => void;
}

export function useReceiptDetails({
	open,
	receiptId,
	providedReceipt,
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
	const [previewState, setPreviewState] = React.useState<{ src: string | null; loading: boolean; refreshing: boolean }>(
		{
			src: null,
			loading: false,
			refreshing: false,
		}
	);

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
		return () => controller.abort();
	}, [open, receiptId, providedReceipt, getToken]);

	// Preview fetch effect
	React.useEffect(() => {
		if (!open || !receiptId) return;
		if (previewAbortRef.current) previewAbortRef.current.abort();
		const controller = new AbortController();
		previewAbortRef.current = controller;
		const cached = previewCache.get(receiptId) || previewCache.get(String(receiptId));
		if (cached) setPreviewState({ src: cached.src, loading: false, refreshing: true });
		else setPreviewState({ src: null, loading: true, refreshing: false });
		(async () => {
			try {
				let token: string | null = null;
				try {
					token = (await getToken?.()) || null;
				} catch {
					/* ignore */
				}
				const auth = token ? { Authorization: `Bearer ${token}` } : undefined;
				const thumb = token
					? `/api/receipts/${encodeURIComponent(receiptId)}/thumb?token=${encodeURIComponent(token)}`
					: `/api/receipts/${encodeURIComponent(receiptId)}/thumb`;
				let chosen: string | null = null;
				try {
					const r = await fetch(thumb, { cache: "no-store", signal: controller.signal });
					if (r.ok && r.headers.get("content-type")?.startsWith("image")) chosen = thumb;
				} catch {
					/* ignore */
				}
				if (!chosen) {
					const dl = await fetchSignedUrlWithRetry(
						`/receipts/${encodeURIComponent(receiptId)}/download_url`,
						auth,
						[300, 700, 1200]
					);
					if (dl) chosen = dl.startsWith("http") ? dl : `${API_URL}${dl}`;
				}
				if (!chosen || controller.signal.aborted) {
					setPreviewState((p) => ({ ...p, loading: false, refreshing: false }));
					return;
				}
				const img = new Image();
				img.addEventListener("load", () => {
					if (controller.signal.aborted) return;
					setPreview(receiptId, chosen!);
					setPreviewState({ src: chosen, loading: false, refreshing: false });
				});
				img.addEventListener("error", () => {
					if (controller.signal.aborted) return;
					setPreviewState((p) => ({ ...p, loading: false, refreshing: false }));
				});
				img.src = chosen.includes("?") ? `${chosen}&cb=${Date.now()}` : `${chosen}?cb=${Date.now()}`;
			} catch {
				if (!controller.signal.aborted) setPreviewState((p) => ({ ...p, loading: false, refreshing: false }));
			}
		})();
		return () => controller.abort();
	}, [open, receiptId, getToken]);

	// SSE update effect (status updates)
	React.useEffect(() => {
		if (!open || !receiptId) return;
		function onUpdate(ev: Event) {
			// CustomEvent detail typing fallback
			const payload: any = (ev as CustomEvent).detail; // eslint-disable-line @typescript-eslint/no-explicit-any
			if (!payload || payload.receipt_id !== receiptId) return;
			setDetailState((prev) => {
				if (!prev.data) return prev;
				const next = { ...prev.data };
				if (payload.status) next.status = String(payload.status).toLowerCase();
				detailCache.set(receiptId, { data: next, ts: Date.now(), partial: false });
				return { ...prev, data: next };
			});
		}
		globalThis.addEventListener("receipt:update", onUpdate);
		return () => globalThis.removeEventListener("receipt:update", onUpdate);
	}, [open, receiptId]);

	const manualRefreshPreview = React.useCallback(() => {
		if (!receiptId) return;
		previewCache.delete(receiptId);
		setPreviewState({ src: null, loading: true, refreshing: false });
	}, [receiptId]);

	// Provide preview with stable cache-busting param like original component
	const previewSrc = React.useMemo(() => {
		if (!previewState.src) return null;
		const hasQuery = previewState.src.includes("?");
		return `${previewState.src}${hasQuery ? "&" : "?"}rid=${encodeURIComponent(String(receiptId || ""))}`;
	}, [previewState.src, receiptId]);

	return {
		receipt: detailState.data,
		loading: detailState.loading,
		refreshing: detailState.refreshing,
		error: detailState.error,
		previewSrc,
		previewLoading: previewState.loading,
		previewRefreshing: previewState.refreshing,
		manualRefreshPreview,
	};
}
