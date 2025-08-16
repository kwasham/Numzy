"use client";

import React from "react";
import { useAuth } from "@clerk/nextjs";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import IconButton from "@mui/material/IconButton";
import Paper from "@mui/material/Paper";
import Skeleton from "@mui/material/Skeleton";
import Stack from "@mui/material/Stack";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import { toast } from "sonner";

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

function statusColor(status: string): "default" | "success" | "error" | "warning" | "info" {
	switch (status) {
		case "completed": {
			return "success";
		}
		case "failed": {
			return "error";
		}
		case "processing": {
			return "warning";
		}
		default: {
			return "default";
		}
	}
}

interface ReceiptsListFilters {
	id?: string;
	merchant?: string;
	status?: string;
	startDate?: string; // ISO date (yyyy-mm-dd) or full ISO string
	endDate?: string; // ISO date (yyyy-mm-dd) or full ISO string
	category?: string;
	subcategory?: string;
}

interface ReceiptsListProps {
	filters?: ReceiptsListFilters;
	sortDir?: "asc" | "desc";
	page?: number; // 0-based
	pageSize?: number;
	view?: string;
	onCountChange?: (count: number) => void;
	onStatsChange?: (stats: {
		countAll: number;
		countCompleted: number;
		countPending: number;
		amountAll: number;
		amountCompleted: number;
		amountPending: number;
	}) => void;
}

export const ReceiptsList: React.FC<ReceiptsListProps> = ({
	filters,
	sortDir = "desc",
	page = 0,
	pageSize = 10,
	view,
	onCountChange,
	onStatsChange,
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
			} catch {
				/* ignore */
			}
			const res = await fetch(`${API_URL}/receipts`, {
				headers: token ? { Authorization: `Bearer ${token}` } : undefined,
			});
			if (!res.ok) throw new Error(`Failed (${res.status})`);
			const data: Receipt[] = await res.json();

			// If we have no category/subcategory data yet, append some mock receipts in dev to aid grouped view testing.
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
					mk(-101, "mock-groceries-2025-08-10.pdf", "Whole Foods", 76.32, "Food & Dining", "Groceries", 2),
					mk(-102, "mock-restaurant-2025-08-11.pdf", "Chipotle", 18.5, "Food & Dining", "Restaurants", 1),
					mk(-103, "mock-rideshare-2025-08-09.pdf", "Uber", 24.9, "Transportation", "Ride Sharing", 3),
					mk(-104, "mock-gas-2025-08-08.pdf", "Shell", 54.21, "Transportation", "Gas", 4),
					mk(-105, "mock-internet-2025-08-01.pdf", "Comcast", 89.99, "Utilities", "Internet", 11),
					mk(-106, "mock-pharmacy-2025-08-07.pdf", "CVS", 12.75, "Health & Wellness", "Pharmacy", 5),
					mk(-107, "mock-clothing-2025-08-05.pdf", "Uniqlo", 43, "Shopping", "Clothing", 7),
					mk(-108, "mock-electronics-2025-08-06.pdf", "Best Buy", 129.99, "Electronics", "Gadgets", 6),
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
		let amountAll = 0;
		let amountCompleted = 0;
		let amountPending = 0;

		for (const r of derived) {
			countAll += 1;
			const ed = (r.extracted_data ?? undefined) as undefined | Record<string, unknown>;
			const totalVal = toNumber(ed?.total);
			amountAll += totalVal;
			const status = (r.status || "").toLowerCase();
			if (status === "completed") {
				countCompleted += 1;
				amountCompleted += totalVal;
			} else if (status === "pending" || status === "processing") {
				countPending += 1;
				amountPending += totalVal;
			}
		}

		onStatsChange({
			countAll,
			countCompleted,
			countPending,
			amountAll,
			amountCompleted,
			amountPending,
		});
	}, [derived, onStatsChange]);

	const paged = React.useMemo(() => {
		if (!derived) return null;
		const startIndex = Math.max(0, page) * Math.max(1, pageSize);
		const endIndex = startIndex + Math.max(1, pageSize);
		return derived.slice(startIndex, endIndex);
	}, [derived, page, pageSize]);

	const grouped = React.useMemo(() => {
		if (!derived) return null;
		// Build category -> subcategory -> rows
		const map = new Map<string, Map<string, Receipt[]>>();
		for (const r of derived) {
			const ed = (r.extracted_data ?? undefined) as undefined | Record<string, unknown>;
			const rawCat = ed?.category as unknown;
			const rawSub = ed?.subcategory as unknown;
			const cat = Array.isArray(rawCat)
				? String(rawCat[0] ?? "Uncategorized")
				: typeof rawCat === "string"
					? rawCat
					: "Uncategorized";
			const sub = Array.isArray(rawSub)
				? String(rawSub[0] ?? "Unspecified")
				: typeof rawSub === "string"
					? rawSub
					: "Unspecified";
			if (!map.has(cat)) map.set(cat, new Map());
			const subMap = map.get(cat)!;
			if (!subMap.has(sub)) subMap.set(sub, []);
			subMap.get(sub)!.push(r);
		}
		// Convert to arrays for stable rendering order
		return [...map.entries()].map(([category, subMap]) => ({
			category,
			subs: [...subMap.entries()].map(([subcategory, rows]) => ({ subcategory, rows })),
		}));
	}, [derived]);

	const refresh = async () => {
		await fetchReceipts();
	};

	const reprocess = async (id: number) => {
		try {
			let token: string | null = null;
			try {
				token = await getToken?.();
			} catch {
				/* ignored */
			}
			const res = await fetch(`${API_URL}/receipts/${id}/reprocess`, {
				method: "POST",
				headers: token ? { Authorization: `Bearer ${token}` } : undefined,
			});
			if (!res.ok) throw new Error(`Reprocess failed (${res.status})`);
			toast.success("Reprocessing queued");
			refresh();
		} catch (error) {
			const msg = error instanceof Error ? error.message : String(error);
			toast.error(msg || "Reprocess failed");
		}
	};

	const download = async (id: number) => {
		try {
			let token: string | null = null;
			try {
				token = await getToken?.();
			} catch {
				/* ignored */
			}
			const res = await fetch(`${API_URL}/receipts/${id}/download`, {
				headers: token ? { Authorization: `Bearer ${token}` } : undefined,
			});
			if (!res.ok) throw new Error("Download URL fetch failed");
			const data = await res.json();
			if (data?.url) {
				const url = data.url.startsWith("http") ? data.url : `${API_URL}${data.url}`;
				window.open(url, "_blank");
			} else {
				throw new Error("No URL returned");
			}
		} catch (error) {
			const msg = error instanceof Error ? error.message : String(error);
			toast.error(msg || "Download failed");
		}
	};

	return (
		<Stack spacing={2}>
			{view === "group" ? (
				<Stack spacing={3} sx={{ width: "100%" }}>
					{loading && (
						<Paper variant="outlined" sx={{ p: 2 }}>
							<Typography variant="body2" color="text.secondary">
								Loading…
							</Typography>
						</Paper>
					)}
					{!loading && (derived?.length ?? 0) === 0 && (
						<Paper variant="outlined" sx={{ p: 2 }}>
							<Typography variant="body2" color="text.secondary">
								No receipts yet. Upload one above.
							</Typography>
						</Paper>
					)}
					{!loading &&
						grouped &&
						grouped.map(({ category, subs }) => (
							<Stack key={category} spacing={1}>
								<Typography variant="h6">{category}</Typography>
								{subs.map(({ subcategory, rows }) => (
									<Stack key={subcategory} spacing={1} sx={{ pl: 2 }}>
										<Typography variant="subtitle2" color="text.secondary">
											{subcategory} — {rows.length} receipt{rows.length === 1 ? "" : "s"}
										</Typography>
										<Paper variant="outlined" sx={{ width: "100%", overflowX: "auto" }}>
											<Box component="table" sx={{ width: "100%", borderCollapse: "collapse" }}>
												<Box component="thead" sx={{ bgcolor: "background.paper" }}>
													<Box component="tr">
														<Box component="th" sx={thSx}>
															Merchant
														</Box>
														<Box component="th" sx={thSx}>
															Amount
														</Box>
														<Box component="th" sx={thSx}>
															Status
														</Box>
														<Box component="th" sx={thSx} />
													</Box>
												</Box>
												<Box component="tbody">
													{rows.map((r) => (
														<Box component="tr" key={r.id}>
															<Cell>{(r.extracted_data as Record<string, unknown> | undefined)?.merchant ?? "—"}</Cell>
															<Cell>
																{(() => {
																	const ed = (r.extracted_data ?? undefined) as undefined | Record<string, unknown>;
																	const raw = ed?.total as unknown;
																	const n =
																		typeof raw === "number"
																			? raw
																			: typeof raw === "string"
																				? Number(raw.replaceAll(/[^0-9.-]+/g, ""))
																				: 0;
																	return Number.isFinite(n) && n !== 0 ? fmtCurrency.format(n) : "—";
																})()}
															</Cell>
															<Cell>
																<Chip
																	size="small"
																	label={r.status}
																	color={statusColor(r.status)}
																	variant={r.status === "pending" ? "outlined" : "filled"}
																/>
															</Cell>
															<Cell>
																<Stack direction="row" spacing={1}>
																	<Tooltip title="Reprocess">
																		<span>
																			<IconButton
																				size="small"
																				onClick={() => reprocess(r.id)}
																				disabled={r.status === "processing" || r.status === "pending"}
																				aria-label="reprocess"
																			>
																				↻
																			</IconButton>
																		</span>
																	</Tooltip>
																	<Tooltip title="Download original">
																		<span>
																			<IconButton size="small" onClick={() => download(r.id)} aria-label="download">
																				⭳
																			</IconButton>
																		</span>
																	</Tooltip>
																	<Button size="small" variant="outlined" onClick={() => setSelected(r)}>
																		View
																	</Button>
																</Stack>
															</Cell>
														</Box>
													))}
												</Box>
											</Box>
										</Paper>
									</Stack>
								))}
							</Stack>
						))}
				</Stack>
			) : (
				<Paper variant="outlined" sx={{ width: "100%", overflowX: "auto" }}>
					<Box component="table" sx={{ width: "100%", borderCollapse: "collapse" }}>
						<Box component="thead" sx={{ bgcolor: "background.paper" }}>
							<Box component="tr">
								<Box component="th" sx={thSx}>
									Merchant
								</Box>
								<Box component="th" sx={thSx}>
									Amount
								</Box>
								<Box component="th" sx={thSx}>
									Status
								</Box>
								<Box component="th" sx={thSx} />
							</Box>
						</Box>
						<Box component="tbody">
							{loading &&
								[1, 2, 3].map((i) => (
									<Box component="tr" key={i}>
										<Cell>
											<Skeleton width={160} />
										</Cell>
										<Cell>
											<Skeleton width={80} />
										</Cell>
										<Cell>
											<Skeleton width={70} />
										</Cell>
										<Cell>
											<Skeleton width={90} />
										</Cell>
									</Box>
								))}
							{!loading && (derived?.length ?? 0) === 0 && (
								<Box component="tr">
									<Cell colSpan={4}>
										<Typography variant="body2" color="text.secondary">
											No receipts yet. Upload one above.
										</Typography>
									</Cell>
								</Box>
							)}
							{!loading &&
								paged &&
								paged.map((r) => (
									<Box component="tr" key={r.id}>
										<Cell>{(r.extracted_data as Record<string, unknown> | undefined)?.merchant ?? "—"}</Cell>
										<Cell>
											{(() => {
												const ed = (r.extracted_data ?? undefined) as undefined | Record<string, unknown>;
												const raw = ed?.total as unknown;
												const n =
													typeof raw === "number"
														? raw
														: typeof raw === "string"
															? Number(raw.replaceAll(/[^0-9.-]+/g, ""))
															: 0;
												return Number.isFinite(n) && n !== 0 ? fmtCurrency.format(n) : "—";
											})()}
										</Cell>
										<Cell>
											<Chip
												size="small"
												label={r.status}
												color={statusColor(r.status)}
												variant={r.status === "pending" ? "outlined" : "filled"}
											/>
										</Cell>
										<Cell>
											<Stack direction="row" spacing={1}>
												<Tooltip title="Reprocess">
													<span>
														<IconButton
															size="small"
															onClick={() => reprocess(r.id)}
															disabled={r.status === "processing" || r.status === "pending"}
															aria-label="reprocess"
														>
															↻
														</IconButton>
													</span>
												</Tooltip>
												<Tooltip title="Download original">
													<span>
														<IconButton size="small" onClick={() => download(r.id)} aria-label="download">
															⭳
														</IconButton>
													</span>
												</Tooltip>
												<Button size="small" variant="outlined" onClick={() => setSelected(r)}>
													View
												</Button>
											</Stack>
										</Cell>
									</Box>
								))}
						</Box>
					</Box>
				</Paper>
			)}

			{/* Detail dialog */}
			<Dialog open={!!selected} onClose={() => setSelected(null)} fullWidth maxWidth="sm">
				<DialogTitle>Receipt Details</DialogTitle>
				<DialogContent dividers>
					{selected ? (
						<Stack spacing={1}>
							<Typography variant="body2">
								<strong>Merchant:</strong>{" "}
								{(selected.extracted_data as Record<string, unknown> | undefined)?.merchant ?? "—"}
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

const thSx = {
	textAlign: "left",
	p: 1,
	fontSize: 12,
	fontWeight: 600,
	borderBottom: (theme) => `1px solid ${theme.palette.divider}`,
} as const;
const tdSx = { p: 1, fontSize: 12, borderBottom: (theme) => `1px solid ${theme.palette.divider}` } as const;

const Cell: React.FC<React.PropsWithChildren<{ colSpan?: number }>> = ({ children, colSpan }) => (
	<Box component="td" colSpan={colSpan} sx={tdSx}>
		{children}
	</Box>
);

export default ReceiptsList;
