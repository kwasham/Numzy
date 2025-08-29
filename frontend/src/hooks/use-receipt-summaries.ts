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
}
async function fetchSummaries(limit: number, token: string | null | undefined): Promise<ReceiptSummary[]> {
	const internalUrl = `/api/receipts/summary?limit=${limit}`;
	const devBypass = process.env.NEXT_PUBLIC_DEV_AUTH_BYPASS === "true" || process.env.DEV_AUTH_BYPASS === "true";
	let internalData: ReceiptSummary[] | null = null;
	let internalMode: string | null = null;
	try {
		// Allow Next.js route-level caching (internal route decides revalidate/tags); avoid no-store here.
		const res = await fetch(internalUrl);
		internalMode = res.headers.get("x-receipts-summary-mode");
		if (res.ok) {
			internalData = (await res.json()) as ReceiptSummary[];
			if (process.env.NODE_ENV !== "production") {
				console.debug("[receipts] internal summary", { count: internalData.length, mode: internalMode });
				if (internalData.length === 0) {
					console.debug("[receipts] internal summary empty", { mode: internalMode, tokenPresent: !!token });
				}
			}
		} else if (process.env.NODE_ENV !== "production") {
			console.warn("[receipts] internal summary non-ok", res.status);
		}
	} catch (error) {
		if (process.env.NODE_ENV !== "production") console.warn("[receipts] internal summary error", error);
	}
	if (internalData && internalData.length > 0) return internalData; // happy path

	// Backend fallback conditions:
	// 1. Dev bypass (as before)
	// 2. OR authenticated client (token present) but internal returned empty/none and mode !== 'auth'
	const allowBackendFallback = devBypass || (token && internalMode !== "auth");
	if (allowBackendFallback && token) {
		try {
			const backendUrl = `${API_URL}/receipts/summary?limit=${limit}`;
			const res = await fetch(backendUrl, {
				headers: { Authorization: `Bearer ${token}` },
				cache: "no-store",
			});
			if (res.ok) {
				const data = (await res.json()) as ReceiptSummary[];
				if (process.env.NODE_ENV !== "production") {
					console.debug("[receipts] backend fallback summary", { count: data.length, devBypass, internalMode });
				}
				return data;
			}
		} catch (error) {
			if (process.env.NODE_ENV !== "production") console.warn("[receipts] backend summary error", error);
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
