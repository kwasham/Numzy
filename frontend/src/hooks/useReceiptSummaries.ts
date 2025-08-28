"use client";

import useSWR from "swr";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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
}

async function fetcher(url: string, token?: string | null) {
	const res = await fetch(url, {
		headers: token ? { Authorization: `Bearer ${token}` } : undefined,
		cache: "no-store",
	});
	if (!res.ok) throw new Error(`Failed ${res.status}`);
	return (await res.json()) as ReceiptSummary[];
}

export function useReceiptSummaries(token: string | null | undefined, limit = 100) {
	return useSWR<ReceiptSummary[]>(
		["/receipts/summary", limit, token ? "auth" : "anon"],
		() => fetcher(`${API_URL}/receipts/summary?limit=${limit}`, token),
		{
			revalidateOnFocus: true,
			dedupingInterval: 4000,
			keepPreviousData: true,
		}
	);
}
