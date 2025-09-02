"use client";

import * as React from "react";
import { useAuth } from "@clerk/nextjs";
import Box from "@mui/material/Box";
import Card from "@mui/material/Card";
import Divider from "@mui/material/Divider";
import Stack from "@mui/material/Stack";

import {
	previewCache,
	primePartialReceipt,
	setPreview,
	shouldAttemptThumb,
} from "@/components/dashboard/receipts/receipt-cache";
import { ReceiptsFilters } from "@/components/dashboard/receipts/receipts-filters";
import { ReceiptsList } from "@/components/dashboard/receipts/receipts-list";
import { ReceiptsPagination } from "@/components/dashboard/receipts/receipts-pagination";
import { ReceiptsSelectionProvider } from "@/components/dashboard/receipts/receipts-selection-context";
import { ReceiptsStats } from "@/components/dashboard/receipts/receipts-stats";
import { ReceiptsTable } from "@/components/dashboard/receipts/receipts-table";
import { ReceiptUploadWidget } from "@/components/widgets/receipt-upload-widget";

export interface ReceiptsContentProps {
	filters?: {
		id?: string;
		merchant?: string;
		status?: string;
		startDate?: string;
		endDate?: string;
		category?: string;
		subcategory?: string;
	};
	sortDir?: "asc" | "desc";
}

// Module-level in-flight map (shared across component instances/renders)
const previewInFlight: Map<string | number, Promise<string | null>> = new Map();

async function prewarmPreview(id: number | string) {
	const existing = previewCache.get(id) || previewCache.get(String(id));
	if (existing?.loaded) return existing.src as string;
	if (previewInFlight.has(id)) return previewInFlight.get(id)!;
	if (previewInFlight.size >= 3) {
		try {
			await Promise.race(previewInFlight.values());
		} catch {
			/* ignore */
		}
	}
	// Do not append the Clerk JWT to the URL; the server API route handles auth and signs a short-lived internal URL.
	const thumb = `/api/receipts/${encodeURIComponent(id)}/thumb`;
	const p: Promise<string | null> = (async () => {
		try {
			if (!shouldAttemptThumb(id)) return null;
			const res = await fetch(thumb, { cache: "no-store" });
			if (!res.ok) return null;
			const ct = res.headers.get("content-type") || "";
			if (!ct.startsWith("image")) return null;
			// Skip proxy placeholders so the modal can perform its own retries and show explicit fallback.
			if (res.headers.get("x-thumb-fallback")) return null;
			const blob = await res.blob();
			if (blob.size < 300) return null; // heuristic: likely 1x1 or tiny placeholder
			const objectUrl = URL.createObjectURL(blob);
			setPreview(id, objectUrl, true, true);
			return objectUrl;
		} finally {
			previewInFlight.delete(id);
		}
	})();
	previewInFlight.set(id, p);
	return p;
}

export function ReceiptsContent({ filters, sortDir = "desc" }: ReceiptsContentProps) {
	const { getToken } = useAuth();
	const [authToken, setAuthToken] = React.useState<string | null>(null);
	React.useEffect(() => {
		let mounted = true;
		(async () => {
			try {
				const t = await getToken?.();
				if (mounted) setAuthToken(t || null);
			} catch {
				if (mounted) setAuthToken(null);
			}
		})();
		return () => {
			mounted = false;
		};
	}, [getToken]);
	const [count, setCount] = React.useState(0);
	const [page, setPage] = React.useState(0);
	const pageSize = 10;
	const [stats, setStats] = React.useState({
		countAll: 0,
		countCompleted: 0,
		countPending: 0,
		countProcessing: 0,
		countFailed: 0,
		amountAll: 0,
		amountCompleted: 0,
		amountPending: 0,
		categories: [] as Array<{ category: string; amount: number; count: number }>,
	});
	// Row type matches the Receipt shape emitted by ReceiptsList onRowsChange
	type ReceiptRow = {
		id: number;
		filename: string;
		status: string;
		extracted_data?: Record<string, unknown> | null;
		audit_decision?: Record<string, unknown> | null;
		created_at: string;
		updated_at: string;
		extraction_progress: number;
		audit_progress: number;
	};
	const [rows, setRows] = React.useState<ReceiptRow[]>([]);

	// Prime cache whenever rows change (only minimal data)
	React.useEffect(() => {
		for (const r of rows) primePartialReceipt(r);
	}, [rows]);

	// Prefetch (blob) preview images for top N completed receipts ahead of any click.
	const PREFETCH_LIMIT = 5;

	React.useEffect(() => {
		let cancelled = false;
		if (!rows || rows.length === 0) return;
		if (authToken === null) return; // still resolving token
		const candidates = rows
			.filter((r) => ["completed", "processed"].includes(r.status?.toLowerCase?.()))
			.slice(0, PREFETCH_LIMIT);
		(async () => {
			for (const r of candidates) {
				if (cancelled) break;
				await prewarmPreview(r.id);
			}
		})();
		return () => {
			cancelled = true;
		};
	}, [rows, authToken]);

	/* prewarmPreview function defined above */

	return (
		<Stack spacing={4} sx={{ flex: "1 1 auto", minWidth: 0 }}>
			{/* Stats at top (keep) */}
			<ReceiptsStats
				_totals={{ all: stats.countAll, completed: stats.countCompleted, failed: 0 }}
				_amounts={{ all: stats.amountAll, completed: stats.amountCompleted, pending: stats.amountPending }}
				categories={stats.categories}
			/>
			{/* Table Card (Orders style) */}
			<ReceiptsSelectionProvider receipts={rows}>
				<Card>
					{/* Orders-like structure: Filters at top, then table, then pagination */}
					<Box sx={{ p: 2 }}>
						<ReceiptsFilters filters={filters || {}} sortDir={sortDir} statusCounts={stats} />
					</Box>
					<Divider />
					<Box sx={{ overflowX: "auto" }}>
						<ReceiptsTable rows={rows} prewarmPreview={prewarmPreview} token={authToken || undefined} />
					</Box>
					<Divider />
					<Box sx={{ p: 2 }}>
						<ReceiptsPagination count={count} page={page} pageSize={pageSize} onPageChange={setPage} />
					</Box>
				</Card>
			</ReceiptsSelectionProvider>

			{/* Headless list to fetch and compute, exposing current paged rows to parent */}
			<ReceiptsList
				filters={filters}
				sortDir={sortDir}
				page={page}
				pageSize={pageSize}
				onCountChange={setCount}
				onStatsChange={setStats}
				renderTable={false}
				onRowsChange={setRows}
			/>
			{/* Uploader lives below the table card as its own component */}
			<Card>
				<Box sx={{ p: 2 }}>
					<ReceiptUploadWidget />
				</Box>
			</Card>
		</Stack>
	);
}

export default ReceiptsContent;
