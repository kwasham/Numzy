"use client";

import React from "react";
import { useAuth } from "@clerk/nextjs";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import { toast } from "sonner";

import { ReceiptsSelectionProvider } from "./receipts-selection-context";
import { ReceiptsTable } from "./receipts-table";

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
	const [loading, setLoading] = React.useState(false);
	const [selected, setSelected] = React.useState<Receipt | null>(null);
	const fmtCurrency = React.useMemo(
		() => new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 2 }),
		[]
	);

	const fetchReceipts = React.useCallback(async () => {
		setLoading(true);
		try {
			let token: string | null = null;
			try {
				token = await getToken?.();
			} catch (error) {
				console.warn("[receipts] getToken failed", error);
			}
			const hasAuth = Boolean(token);
			const res = await fetch(`${API_URL}/receipts`, {
				headers: hasAuth ? { Authorization: `Bearer ${token}` } : undefined,
			});
			if (!res.ok) {
				if (res.status === 401 || res.status === 403) {
					toast.error("Not authorized – sign in required");
					console.error(`[receipts] auth failure status=${res.status} hasAuthHeader=${hasAuth}`);
				} else {
					toast.error(`Failed to load receipts (${res.status})`);
				}
				setReceipts([]);
				return;
			}
			const data: Receipt[] = await res.json();

			const hasCategoryOrSub = (arr: Receipt[]) =>
				arr.some((r) => {
					const ed = (r.extracted_data ?? undefined) as undefined | Record<string, unknown>;
					const cat = ed?.category;
					const sub = ed?.subcategory;
					return typeof cat === "string" || Array.isArray(cat) || typeof sub === "string" || Array.isArray(sub);
				});

			const buildMockReceipts = (): Receipt[] => {
				const now = Date.now();
				const mk = (
					id: number,
					filename: string,
					merchant: string,
					total: number,
					category: string,
					subcategory: string,
					daysAgo: number
				): Receipt => {
					const ts = new Date(now - daysAgo * 24 * 60 * 60 * 1000).toISOString();
					return {
						id,
						filename,
						status: "completed",
						extracted_data: { merchant, total, category, subcategory },
						audit_decision: null,
						created_at: ts,
						updated_at: ts,
						extraction_progress: 100,
						audit_progress: 100,
					};
				};

				return [
					mk(
						-101,
						"mock-groceries-2025-08-10.pdf",
						"Whole Foods",
						76.32,
						"Meals and Entertainment",
						"Employee Meals (team outings, working lunches)",
						2
					),
					mk(-102, "mock-restaurant-2025-08-11.pdf", "Chipotle", 18.5, "Meals and Entertainment", "Client Meals", 1),
					mk(
						-103,
						"mock-rideshare-2025-08-09.pdf",
						"Uber",
						24.9,
						"Travel Specific Expenses",
						"Ground Transportation (Taxi, Ride-share, Rental Car)",
						3
					),
					mk(-104, "mock-gas-2025-08-08.pdf", "Shell", 54.21, "Operational Expenses", "Fuel", 4),
					mk(
						-105,
						"mock-internet-2025-08-01.pdf",
						"Comcast",
						89.99,
						"Operational Expenses",
						"Utilities (Electricity, Water, Internet)",
						11
					),
					mk(
						-106,
						"mock-pharmacy-2025-08-07.pdf",
						"CVS",
						12.75,
						"Other",
						"Anything used for your business but is not a day to day expense. (Training and development, penalties or fines, bank fees)",
						5
					),
					mk(
						-107,
						"mock-clothing-2025-08-05.pdf",
						"Uniqlo",
						43,
						"Other",
						"Anything used for your business but is not a day to day expense. (Training and development, penalties or fines, bank fees)",
						7
					),
					mk(-108, "mock-electronics-2025-08-06.pdf", "Best Buy", 129.99, "Operational Expenses", "Office Supplies", 6),
				];
			};

			if (process.env.NODE_ENV !== "production" && !hasCategoryOrSub(data)) {
				data.push(...buildMockReceipts());
			}

			// Sort by created_at desc (mock entries included)
			data.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
			setReceipts(data);
		} catch (error) {
			const msg = error instanceof Error ? error.message : String(error);
			toast.error(msg || "Failed to load receipts");
			setReceipts([]);
		} finally {
			setLoading(false);
		}
	}, [getToken]);

	React.useEffect(() => {
		fetchReceipts();
	}, [fetchReceipts]);

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

		const toNumber = (val: unknown): number => {
			if (typeof val === "number") return Number.isFinite(val) ? val : 0;
			if (typeof val === "string") {
				const cleaned = val.replaceAll(/[^0-9.-]+/g, "");
				const n = Number(cleaned);
				return Number.isFinite(n) ? n : 0;
			}
			return 0;
		};

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
			const totalVal = toNumber(ed?.total);
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

	if (!renderTable) {
		// Headless mode: only side-effects; parent renders the table
		return null;
	}

	return (
		<Stack spacing={2}>
			{loading ? (
				<Paper variant="outlined" sx={{ p: 2 }}>
					<Typography variant="body2" color="text.secondary">
						Loading…
					</Typography>
				</Paper>
			) : (
				<ReceiptsSelectionProvider receipts={paged ?? []}>
					<ReceiptsTable rows={paged ?? []} />
				</ReceiptsSelectionProvider>
			)}
			<Dialog open={!!selected} onClose={() => setSelected(null)} fullWidth maxWidth="sm">
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
