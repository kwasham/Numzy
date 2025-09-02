"use client";

import useSWR from "swr";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Internal route handles backend communication & caching; no direct API_URL use here.

export interface ReceiptSummary {
	id: number;
	filename?: string | null;
	status: string;
	created_at: string;
	updated_at?: string | null;
	extraction_progress?: number | null;
	audit_progress?: number | null;
	merchant?: string | null;
	total?: number | null;
	payment_type?: string | null;
	payment_brand?: string | null;
	payment_last4?: string | null;
	extracted_data?: Record<string, unknown> | null; // full extracted_data now available
}
async function fetchSummaries(limit: number, token: string | null | undefined): Promise<ReceiptSummary[]> {
	const internalUrl = `/api/receipts/summary?limit=${limit}`;
	let internalData: ReceiptSummary[] | null = null;
	let internalMode: string | null = null;
	try {
		const res = await fetch(internalUrl);
		internalMode = res.headers.get("x-receipts-summary-mode");
		if (res.ok) {
			internalData = (await res.json()) as ReceiptSummary[];
			if (process.env.NODE_ENV !== "production") {
				console.debug("[receipts] internal summary", { count: internalData.length, mode: internalMode });
			}
		} else if (process.env.NODE_ENV !== "production") {
			console.warn("[receipts] internal summary non-ok", res.status);
		}
	} catch (error) {
		if (process.env.NODE_ENV !== "production") console.warn("[receipts] internal summary error", error);
	}

	// If we have a user token and internal mode is not 'auth', prefer backend to avoid stale anon cache.
	const shouldPreferBackend = !!token && internalMode !== "auth";
	if (shouldPreferBackend && token) {
		try {
			const backendUrl = `${API_URL}/receipts/summary?limit=${limit}`;
			const res = await fetch(backendUrl, {
				headers: { Authorization: `Bearer ${token}` },
				cache: "no-store",
			});
			if (res.ok) {
				const data = (await res.json()) as ReceiptSummary[];
				if (process.env.NODE_ENV !== "production") {
					console.debug("[receipts] backend preferred summary", { count: data.length, internalMode });
				}
				return data;
			}
		} catch (error) {
			if (process.env.NODE_ENV !== "production") console.warn("[receipts] backend summary error", error);
		}
	}

	// Otherwise, if internal returned data (auth or anon) use it.
	if (internalData && internalData.length > 0) return internalData;

	// Final fallback: backend if token (even when internal empty)
	if (token) {
		try {
			const backendUrl = `${API_URL}/receipts/summary?limit=${limit}`;
			const res = await fetch(backendUrl, {
				headers: { Authorization: `Bearer ${token}` },
				cache: "no-store",
			});
			if (res.ok) return (await res.json()) as ReceiptSummary[];
		} catch {
			/* ignore */
		}
	}
	return internalData || [];
}

export function useReceiptSummaries(token: string | null | undefined, limit = 100) {
	return useSWR<ReceiptSummary[]>(["/receipts/summary", limit, token ? "t" : ""], () => fetchSummaries(limit, token), {
		revalidateOnFocus: false,
		dedupingInterval: 5000,
		keepPreviousData: true,
	});
}
