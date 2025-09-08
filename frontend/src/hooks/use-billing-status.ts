"use client";

import * as React from "react";
import { useAuth } from "@clerk/nextjs";

import { BillingStatus, fetchBillingStatus } from "@/lib/billing-client";

interface Options {
	refreshIntervalMs?: number; // optional polling (disabled by default)
}

export function useBillingStatus(opts: Options = {}) {
	const { getToken } = useAuth();
	const { refreshIntervalMs } = opts;
	const [status, setStatus] = React.useState<BillingStatus | null>(null);
	const [loading, setLoading] = React.useState(true);
	const [error, setError] = React.useState<string | null>(null);

	const load = React.useCallback(async () => {
		try {
			setLoading(true);
			setError(null);
			const st = await fetchBillingStatus(getToken);
			setStatus(st);
		} catch (error_) {
			setError((error_ as Error)?.message || "Failed to load billing status");
		} finally {
			setLoading(false);
		}
	}, [getToken]);

	React.useEffect(() => {
		load();
	}, [load]);

	// Optional light polling
	React.useEffect(() => {
		if (!refreshIntervalMs) return;
		const id = setInterval(() => {
			load();
		}, refreshIntervalMs);
		return () => clearInterval(id);
	}, [refreshIntervalMs, load]);

	return { status, loading, error, refresh: load };
}
