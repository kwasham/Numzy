"use client";

import React from "react";
import { useAuth } from "@clerk/nextjs";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import LinearProgress from "@mui/material/LinearProgress";
import Paper from "@mui/material/Paper";
import Skeleton from "@mui/material/Skeleton";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import { toast } from "sonner";

import { parseAmount } from "@/lib/parse-amount";
import { useReceiptSummaries } from "@/hooks/use-receipt-summaries";

import { ReceiptsSelectionProvider } from "./receipts-selection-context";
import { ReceiptsTable } from "./receipts-table";

type AmountLike = number | string | null | undefined;

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Receipt {
	id: number;
	filename: string;
	status: string;
	extracted_data?: Record<string, unknown> | null;
	audit_decision?: Record<string, unknown> | null;
	created_at: string;
	updated_at: string;
	extraction_progress: number;
	audit_progress: number;
}

interface ReceiptsListFilters {
	id?: string;
	merchant?: string;
	status?: string;
	startDate?: string;
	endDate?: string;
	category?: string;
	subcategory?: string;
}

interface ReceiptsListProps {
	filters?: ReceiptsListFilters;
	sortDir?: "asc" | "desc";
	page?: number;
	pageSize?: number;
	onCountChange?: (count: number) => void;
	onStatsChange?: (stats: {
		countAll: number;
		countCompleted: number;
		countPending: number;
		countProcessing: number;
		countFailed: number;
		amountAll: number;
		amountCompleted: number;
		amountPending: number;
		categories: Array<{ category: string; amount: number; count: number }>;
	}) => void;
	// When false, the component won't render the table UI; it will only fetch/derive data
	// and emit callbacks (onCountChange, onStatsChange, onRowsChange).
	renderTable?: boolean;
	// Emits the current paged rows so a parent can render the table and wrap with selection provider.
	onRowsChange?: (rows: Receipt[]) => void;
}

export const ReceiptsList: React.FC<ReceiptsListProps> = ({
	filters,
	sortDir = "desc",
	page = 0,
	pageSize = 10,
	onCountChange,
	onStatsChange,
	renderTable = true,
	onRowsChange,
}) => {
	const { getToken } = useAuth();
	const [receipts, setReceipts] = React.useState<Receipt[] | null>(null);
	const [selected, setSelected] = React.useState<Receipt | null>(null);
	const fmtCurrency = React.useMemo(
		() => new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 2 }),
		[]
	);
	// (Removed prevStatusRef; SSE updates manage completion toasts directly)

	// Auth token (once) so summary endpoint can leverage per-user server caching
	const [authToken, setAuthToken] = React.useState<string | null | undefined>(null);
	React.useEffect(() => {
		let mounted = true;
		(async () => {
			try {
				const t = await getToken?.();
				if (mounted) setAuthToken(t);
			} catch {
				/* ignore */
			}
		})();
		return () => {
			mounted = false;
		};
	}, [getToken]);
	// FAST SUMMARY (cached) for initial paint (token may be null briefly; SWR will refetch when it appears)
	const { data: summary, isLoading: summaryLoading } = useReceiptSummaries(authToken, 300);
	React.useEffect(() => {
		if (summary && (!receipts || receipts.length === 0)) {
			setReceipts(
				summary.map((s) => ({
					id: s.id,
					filename: s.filename || `receipt-${s.id}`,
					status: s.status,
					extracted_data: s.merchant ? { merchant: s.merchant, total: s.total } : null,
					audit_decision: null,
					created_at: s.created_at,
					updated_at: s.updated_at || s.created_at,
					extraction_progress: s.extraction_progress || 0,
					audit_progress: s.audit_progress || 0,
				}))
			);
		}
	}, [summary, receipts]);

	// Optimistic insertion of newly uploaded receipt so the table shows it instantly with progress bar
	React.useEffect(() => {
		interface UploadedDetail {
			id: number;
			filename?: string;
			status?: string;
			extracted_data?: Record<string, unknown> | null;
			audit_decision?: Record<string, unknown> | null;
			created_at?: string;
			updated_at?: string;
			extraction_progress?: number;
			audit_progress?: number;
		}
		function onUploaded(e: Event) {
			const detail = (e as CustomEvent).detail as UploadedDetail | undefined;
			if (!detail || typeof detail !== "object" || !detail.id) return;
			setReceipts((prev) => {
				const existing = prev || [];
				// Avoid duplicate if already present
				if (existing.some((r) => r.id === detail.id)) return existing;
				const optimistic: Receipt = {
					id: detail.id,
					filename: detail.filename || "uploading…",
					status: (detail.status || "processing").toLowerCase(),
					extracted_data: detail.extracted_data || null,
					audit_decision: detail.audit_decision || null,
					created_at: detail.created_at || new Date().toISOString(),
					updated_at: detail.updated_at || new Date().toISOString(),
					extraction_progress: detail.extraction_progress ?? 0,
					audit_progress: detail.audit_progress ?? 0,
				};
				return [optimistic, ...existing];
			});
		}
		globalThis.addEventListener("receipt:uploaded", onUploaded as EventListener);
		return () => globalThis.removeEventListener("receipt:uploaded", onUploaded as EventListener);
	}, []);

	// SSE real-time updates (replaces polling)
	React.useEffect(() => {
		let es: EventSource | null = null;
		let cancelled = false;
		let retryTimeout: NodeJS.Timeout | null = null;

		const handleMessage = (ev: MessageEvent) => {
			try {
				const payload = JSON.parse(ev.data);
				if (!payload || typeof payload !== "object" || !("receipt_id" in payload)) return;
				// Broadcast globally so other components (like an open modal) can react
				globalThis.dispatchEvent(new CustomEvent("receipt:update", { detail: payload }));
				setReceipts((prev) => {
					const list = prev ? [...prev] : [];
					const idx = list.findIndex((r) => r.id === payload.receipt_id);
					if (idx === -1) return prev; // unknown id: ignore
					const r = { ...list[idx] };
					if (payload.status) r.status = String(payload.status).toLowerCase();
					if (payload.progress && typeof payload.progress === "object") {
						if (typeof payload.progress.extraction === "number") r.extraction_progress = payload.progress.extraction;
						if (typeof payload.progress.audit === "number") r.audit_progress = payload.progress.audit;
					}
					list[idx] = r;
					if (payload.type === "receipt.completed") {
						toast.success(`Receipt ${r.filename || r.id} processed`);
					}
					return list;
				});
			} catch {
				/* ignore */
			}
		};

		const connect = async () => {
			let _token: string | null = null;
			try {
				_token = await getToken?.();
			} catch {
				/* ignore token error */
			}
			if (cancelled) return;
			const url = new URL(`${API_URL}/receipts/events`);
			// If needed, could pass token in a custom header via EventSource polyfill; omitted for now.
			es = new EventSource(url.toString(), { withCredentials: true });
			const onError = () => {
				if (es) es.close();
				if (cancelled) return;
				retryTimeout = setTimeout(connect, 2000);
			};
			es.addEventListener("message", handleMessage);
			es.addEventListener("error", onError);
		};
		void connect();
		return () => {
			cancelled = true;
			if (retryTimeout) clearTimeout(retryTimeout);
			if (es) es.close();
		};
	}, [getToken]);

	// Derived rows with client-side filtering & sorting
	const derived = React.useMemo(() => {
		if (!receipts) return null;
		let rows = [...receipts];

		// Filtering
		const f = filters || {};
		const idQuery = (f.id || "").trim();
		const merchantQuery = (f.merchant || "").toLowerCase().trim();
		const statusQuery = (f.status || "").toLowerCase().trim();
		const categoryQuery = (f.category || "").toLowerCase().trim();
		const subcategoryQuery = (f.subcategory || "").toLowerCase().trim();

		const start = f.startDate ? new Date(f.startDate) : null;
		const end = f.endDate ? new Date(f.endDate) : null;

		rows = rows.filter((r) => {
			// id filter: match id or filename substring
			if (idQuery) {
				const idMatch = String(r.id).includes(idQuery);
				const fileMatch = r.filename.toLowerCase().includes(idQuery.toLowerCase());
				if (!idMatch && !fileMatch) return false;
			}

			// merchant filter: check extracted_data["merchant"] contains
			if (merchantQuery) {
				const ed =
					r.extracted_data && typeof r.extracted_data === "object"
						? (r.extracted_data as Record<string, unknown>)
						: undefined;
				const merchantRaw = ed ? ed["merchant"] : undefined;
				const merchant =
					typeof merchantRaw === "string"
						? merchantRaw.toLowerCase()
						: typeof merchantRaw === "number"
							? String(merchantRaw).toLowerCase()
							: "";
				if (!merchant.includes(merchantQuery)) return false;
			}

			// status filter: exact match if provided and not 'all'
			if (statusQuery && statusQuery !== "all" && r.status.toLowerCase() !== statusQuery) {
				return false;
			}

			// category/subcategory filters (match on extracted_data.category / extracted_data.subcategory)
			if (categoryQuery || subcategoryQuery) {
				const ed =
					r.extracted_data && typeof r.extracted_data === "object"
						? (r.extracted_data as Record<string, unknown>)
						: undefined;

				const toValues = (val: unknown): string[] => {
					if (typeof val === "string" || typeof val === "number") return [String(val).toLowerCase()];
					if (Array.isArray(val)) return val.map((v) => String(v).toLowerCase());
					return [];
				};

				const catVals = toValues(ed ? (ed["category"] as unknown) : undefined);
				const subVals = toValues(ed ? (ed["subcategory"] as unknown) : undefined);

				if (categoryQuery && !catVals.some((v) => v.includes(categoryQuery))) return false;
				if (subcategoryQuery && !subVals.some((v) => v.includes(subcategoryQuery))) return false;
			}

			// date range filter: compare created_at
			if (start || end) {
				const created = new Date(r.created_at);
				if (Number.isNaN(created.getTime())) return false;
				if (start && created < start) return false;
				if (end) {
					// include the whole end day if date-only string
					const endAdj = f.endDate && f.endDate.length === 10 ? new Date(end.getTime() + 24 * 60 * 60 * 1000) : end;
					if (created >= (endAdj as Date)) return false;
				}
			}

			return true;
		});

		// Sorting by created_at
		rows.sort((a, b) => {
			const aT = new Date(a.created_at).getTime();
			const bT = new Date(b.created_at).getTime();
			return sortDir === "asc" ? aT - bT : bT - aT;
		});

		return rows;
	}, [receipts, filters, sortDir]);

	// Inform parent of total count
	React.useEffect(() => {
		if (derived && typeof onCountChange === "function") {
			onCountChange(derived.length);
		}
	}, [derived, onCountChange]);

	// Emit stats (counts and amounts) for the current filtered set
	React.useEffect(() => {
		if (!derived || typeof onStatsChange !== "function") return;

		const toNumber = (val: AmountLike): number => parseAmount(val as AmountLike);

		let countAll = 0;
		let countCompleted = 0;
		let countPending = 0;
		let countProcessing = 0;
		let countFailed = 0;
		let amountAll = 0;
		let amountCompleted = 0;
		let amountPending = 0;
		const catMap = new Map<string, { amount: number; count: number }>();

		for (const r of derived) {
			countAll += 1;
			const ed = (r.extracted_data ?? undefined) as undefined | Record<string, unknown>;
			const totalVal = toNumber(
				(ed?.total as AmountLike) ?? (ed?.amount_total as AmountLike) ?? (ed?.amount as AmountLike)
			);
			amountAll += totalVal;
			const status = (r.status || "").toLowerCase();
			switch (status) {
				case "completed": {
					countCompleted += 1;
					amountCompleted += totalVal;
					break;
				}
				case "pending": {
					countPending += 1;
					amountPending += totalVal;
					break;
				}
				case "processing": {
					countPending += 1; // treat as pending for amount bucketing
					amountPending += totalVal;
					countProcessing += 1;
					break;
				}
				case "failed": {
					countFailed += 1;
					break;
				}
				default: {
					break;
				}
			}

			// category tally
			const rawCat = ed?.category as unknown;
			const category = Array.isArray(rawCat)
				? String(rawCat[0] ?? "Uncategorized")
				: typeof rawCat === "string"
					? rawCat
					: "Uncategorized";
			const cur = catMap.get(category) || { amount: 0, count: 0 };
			cur.amount += totalVal;
			cur.count += 1;
			catMap.set(category, cur);
		}

		const categories = [...catMap.entries()]
			.map(([category, v]) => ({ category, amount: v.amount, count: v.count }))
			.sort((a, b) => {
				if (a.amount === b.amount) return b.count - a.count;
				return b.amount - a.amount;
			});

		onStatsChange({
			countAll,
			countCompleted,
			countPending,
			countProcessing,
			countFailed,
			amountAll,
			amountCompleted,
			amountPending,
			categories,
		});
	}, [derived, onStatsChange]);

	const paged = React.useMemo(() => {
		if (!derived) return null;
		const startIndex = Math.max(0, page) * Math.max(1, pageSize);
		const endIndex = startIndex + Math.max(1, pageSize);
		return derived.slice(startIndex, endIndex);
	}, [derived, page, pageSize]);

	// Let parent know the visible rows for this page
	React.useEffect(() => {
		if (paged && Array.isArray(paged)) {
			onRowsChange?.(paged);
		}
	}, [paged, onRowsChange]);

	// Group view removed

	// No reprocess/download actions in list view (kept minimal)

	// Compute a simple overall extraction progress indicator for UI
	const overallProgress = React.useMemo(() => {
		const list = receipts || [];
		const inflight = list.filter((r) => {
			const s = (r.status || "").toLowerCase();
			return s === "pending" || s === "processing";
		});
		if (inflight.length === 0) return null;
		const vals = inflight.map((r) => (Number.isFinite(r.extraction_progress) ? r.extraction_progress : 0));
		const avg = vals.length > 0 ? Math.round(vals.reduce((a, b) => a + b, 0) / vals.length) : 0;
		return { count: inflight.length, avg };
	}, [receipts]);

	const hasInFlight = React.useMemo(
		() => (receipts || []).some((r) => ["pending", "processing"].includes((r.status || "").toLowerCase())),
		[receipts]
	);

	const ProgressBanner = hasInFlight ? (
		<Paper variant="outlined" sx={{ p: 2 }}>
			<Stack spacing={1}>
				<Typography variant="body2" color="text.secondary">
					Extracting data for recent uploads… {overallProgress ? `(avg ${overallProgress.avg}%)` : ""}
				</Typography>
				<LinearProgress variant={overallProgress ? "determinate" : "indeterminate"} value={overallProgress?.avg ?? 0} />
			</Stack>
		</Paper>
	) : null;

	if (!renderTable) {
		// Headless mode: still show progress banner if any items are inflight
		return ProgressBanner;
	}

	return (
		<Stack spacing={2}>
			{ProgressBanner}
			{summaryLoading && !receipts ? (
				<Paper variant="outlined" sx={{ p: 2 }}>
					{Array.from({ length: 6 }).map((_, i) => (
						<Stack key={i} direction="row" spacing={2} sx={{ alignItems: "center", py: 1 }}>
							<Skeleton variant="rectangular" width={48} height={40} />
							<Stack spacing={0.5} sx={{ flex: 1 }}>
								<Skeleton variant="text" width={160} />
								<Skeleton variant="text" width={120} />
							</Stack>
							<Skeleton variant="text" width={90} />
							<Skeleton variant="circular" width={32} height={32} />
						</Stack>
					))}
				</Paper>
			) : (
				<ReceiptsSelectionProvider receipts={paged ?? []}>
					<ReceiptsTable rows={paged ?? []} />
				</ReceiptsSelectionProvider>
			)}
			<Dialog key={selected?.id || "none"} open={!!selected} onClose={() => setSelected(null)} fullWidth maxWidth="sm">
				<DialogTitle>Receipt Details</DialogTitle>
				<DialogContent dividers>
					{selected ? (
						<Stack spacing={1}>
							<Typography variant="body2">
								<strong>Merchant:</strong>{" "}
								{String((selected.extracted_data as Record<string, unknown> | undefined)?.merchant ?? "—")}
							</Typography>
							<Typography variant="body2">
								<strong>Amount:</strong>{" "}
								{(() => {
									const ed = (selected.extracted_data ?? undefined) as undefined | Record<string, unknown>;
									const raw = ed?.total as unknown;
									const n =
										typeof raw === "number"
											? raw
											: typeof raw === "string"
												? Number(raw.replaceAll(/[^0-9.-]+/g, ""))
												: 0;
									return Number.isFinite(n) && n !== 0 ? fmtCurrency.format(n) : "—";
								})()}
							</Typography>
							<Typography variant="body2">
								<strong>Status:</strong> {selected.status}
							</Typography>
							<Typography variant="body2">
								<strong>File:</strong> {selected.filename}
							</Typography>
							<Typography variant="body2">
								<strong>Created:</strong> {new Date(selected.created_at).toLocaleString()}
							</Typography>
							<Typography variant="body2" sx={{ mt: 1 }}>
								<strong>Extracted data:</strong>
							</Typography>
							<Box component="pre" sx={{ m: 0, p: 1, bgcolor: "action.hover", borderRadius: 1, overflow: "auto" }}>
								{JSON.stringify(selected.extracted_data ?? {}, null, 2)}
							</Box>
						</Stack>
					) : null}
				</DialogContent>
				<DialogActions>
					<Button onClick={() => setSelected(null)}>Close</Button>
				</DialogActions>
			</Dialog>
		</Stack>
	);
};

export default ReceiptsList;
