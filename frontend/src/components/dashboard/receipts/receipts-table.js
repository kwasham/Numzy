"use client";

import * as React from "react";
import RouterLink from "next/link";
import { useAuth } from "@clerk/nextjs";
import Avatar from "@mui/material/Avatar";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import IconButton from "@mui/material/IconButton";
import LinearProgress from "@mui/material/LinearProgress";
import Link from "@mui/material/Link";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import { CheckCircleIcon } from "@phosphor-icons/react/dist/ssr/CheckCircle";
import { ClockIcon } from "@phosphor-icons/react/dist/ssr/Clock";
import { EyeIcon } from "@phosphor-icons/react/dist/ssr/Eye";
import { MinusIcon } from "@phosphor-icons/react/dist/ssr/Minus";
import { XCircleIcon } from "@phosphor-icons/react/dist/ssr/XCircle";
import { toast } from "sonner";

import { paths } from "@/paths";
import { dayjs } from "@/lib/dayjs";
import { parseAmount } from "@/lib/parse-amount";
import { DataTable } from "@/components/core/data-table";
import { RECEIPT_CATEGORY_MAP } from "@/components/dashboard/receipts/categories";
import {
	markThumbFailure,
	previewCache,
	setPreview,
	shouldAttemptThumb,
} from "@/components/dashboard/receipts/receipt-cache";

import { useReceiptsSelection } from "./receipts-selection-context";

// Fetch Clerk token once (no refresh logic needed for short-lived prefetch)
function useTokenOnce() {
	const { getToken } = useAuth();
	const [token, setToken] = React.useState();
	React.useEffect(() => {
		let cancelled = false;
		(async () => {
			try {
				const t = await getToken?.();
				if (!cancelled) setToken(t || "");
			} catch {
				if (!cancelled) setToken("");
			}
		})();
		return () => {
			cancelled = true;
		};
	}, [getToken]);
	return token;
}

// Adapter to map receipt rows into the shape expected by the Orders table columns
function toDisplayRow(r) {
	const ed = r.extracted_data && typeof r.extracted_data === "object" ? r.extracted_data : {};
	const merchant = ed.merchant ?? ed.vendor ?? ed.merchant_name ?? "—";
	const totalRaw = ed.total ?? ed.amount_total ?? ed.amount;
	const totalAmount = parseAmount(totalRaw);

	// Transaction date: prefer extracted time value if parsable, else fallback to created_at
	let transactionDate = new Date(r.created_at);
	const timeRaw = ed.time || ed.transaction_time || ed.transactionDate || null;
	if (timeRaw) {
		// Attempt parse with dayjs; fallback to Date constructor
		const candidate = dayjs(timeRaw);
		if (candidate.isValid()) {
			transactionDate = candidate.toDate();
		} else {
			const alt = new Date(timeRaw);
			if (!Number.isNaN(alt.getTime())) transactionDate = alt;
		}
	}

	// Derive payment method (brand + last4) if present in extracted data
	const pmSource = ed.payment_method || ed.payment || ed.card || null;
	let paymentMethod = null;
	if (pmSource && typeof pmSource === "object") {
		// candidate brand/type fields
		const rawBrand =
			pmSource.brand || pmSource.type || pmSource.card_brand || pmSource.scheme || pmSource.network || "";
		const norm = String(rawBrand)
			.toLowerCase()
			.replaceAll(/[^a-z0-9]/g, "");
		const brandMap = {
			visa: "visa",
			mastercard: "mastercard",
			mc: "mastercard",
			americanexpress: "amex",
			amex: "amex",
			applepay: "applepay",
			apple: "applepay",
			googlepay: "googlepay",
			google: "googlepay",
		};
		const type = brandMap[norm] || norm || null;
		const last4 =
			pmSource.last4 ||
			pmSource.card_last4 ||
			(pmSource.number && String(pmSource.number).slice(-4)) ||
			(pmSource.card_number && String(pmSource.card_number).slice(-4)) ||
			null;
		if (type) {
			paymentMethod = { type, brand: rawBrand, last4 };
		}
	}
	return {
		id: r.id,
		createdAt: new Date(r.created_at),
		transactionDate,
		lineItems: 1,
		paymentMethod,
		currency: "USD",
		totalAmount,
		status: r.status,
		extractionProgress: r.extraction_progress ?? 0,
		customer: { name: merchant, avatar: undefined, email: undefined },
	};
}

const columns = (token, prewarmPreview, handleCategoryChange) => [
	{
		formatter: (row) => (
			<Stack
				direction="row"
				spacing={2}
				sx={{ alignItems: "center" }}
				onMouseEnter={() => {
					// If we ever want to prefetch preview on hover, trigger lightweight fetch here
					// Skip if preview already cached
					if (!token) return; // avoid 401/403 spam before auth ready
					if (previewCache.get(row.id) || previewCache.get(String(row.id))) return;
					if (!shouldAttemptThumb(row.id)) return; // cooldown
					const thumb = `/api/receipts/${encodeURIComponent(row.id)}/thumb`;
					try {
						const img = new Image();
						img.addEventListener("load", () => setPreview(row.id, thumb, true));
						img.addEventListener("error", () => markThumbFailure(row.id));
						// Append lightweight pre param (cache-busting without conflicting with later rid param logic)
						img.src = `${thumb}${thumb.includes("?") ? "&" : "?"}pre=1`;
					} catch {
						/* ignore */
					}
				}}
			>
				<Box
					sx={{
						bgcolor: "var(--mui-palette-background-level1)",
						borderRadius: 1.5,
						flex: "0 0 auto",
						p: "4px 8px",
						textAlign: "center",
					}}
				>
					<Typography variant="caption">{dayjs(row.createdAt).format("MMM").toUpperCase()}</Typography>
					<Typography variant="h6">{dayjs(row.createdAt).format("D")}</Typography>
				</Box>
				<div style={{ minWidth: 160 }}>
					<Link
						color="text.primary"
						component={RouterLink}
						href={paths.dashboard.receiptsPreview(row.id)}
						sx={{ cursor: "pointer" }}
						onClick={(e) => {
							// Intercept to ensure blob is prefetched before navigation for instant modal image.
							if (previewCache.get(row.id)?.loaded) return; // already ready, allow default
							if (prewarmPreview) {
								e.preventDefault();
								prewarmPreview(row.id).then(() => {
									// After prewarm push shallow to update URL (modal will open)
									globalThis.history.pushState({}, "", paths.dashboard.receiptsPreview(row.id));
									// Dispatch a popstate-based custom event if needed (Next router already notices search param change in App Router env)
								});
							}
						}}
						onFocus={() => {
							// Preload on keyboard focus as well
							if (previewCache.get(row.id) || previewCache.get(String(row.id))) return;
							const thumb = `/api/receipts/${encodeURIComponent(row.id)}/thumb`;
							try {
								if (!shouldAttemptThumb(row.id)) return; // cooldown
								const img = new Image();
								img.addEventListener("load", () => setPreview(row.id, thumb, true));
								img.addEventListener("error", () => markThumbFailure(row.id));
								img.src = `${thumb}${thumb.includes("?") ? "&" : "?"}pre=1`;
							} catch {
								/* ignore */
							}
						}}
						variant="subtitle2"
					>
						{row.customer.name}
					</Link>
					<Typography variant="body2" color="text.secondary" sx={{ lineHeight: 1.3 }}>
						{row.totalAmount != null && !Number.isNaN(row.totalAmount)
							? new Intl.NumberFormat("en-US", { style: "currency", currency: row.currency || "USD" }).format(
									row.totalAmount
								)
							: "—"}
					</Typography>
					{(row.status === "pending" || row.status === "processing") && (
						<Box sx={{ mt: 0.5 }}>
							<LinearProgress
								variant={row.extractionProgress > 0 ? "determinate" : "indeterminate"}
								value={row.extractionProgress || 0}
								sx={{ height: 6, borderRadius: 3, width: 140, bgcolor: "background.default" }}
							/>
						</Box>
					)}
				</div>
			</Stack>
		),
		name: "Receipt",
		width: "250px",
	},
	{
		formatter: (row) => {
			if (!row.paymentMethod) return null;

			const mapping = {
				mastercard: { name: "Mastercard", logo: "/assets/payment-method-1.png" },
				visa: { name: "Visa", logo: "/assets/payment-method-2.png" },
				amex: { name: "American Express", logo: "/assets/payment-method-3.png" },
				applepay: { name: "Apple Pay", logo: "/assets/payment-method-4.png" },
				googlepay: { name: "Google Pay", logo: "/assets/payment-method-5.png" },
			};
			const { name, logo } = mapping[row.paymentMethod.type] ?? { name: "Unknown", logo: null };

			return (
				<Stack direction="row" spacing={2} sx={{ alignItems: "center" }}>
					<Avatar sx={{ bgcolor: "var(--mui-palette-background-paper)", boxShadow: "var(--mui-shadows-8)" }}>
						<Box component="img" src={logo} sx={{ borderRadius: "50px", height: "auto", width: "35px" }} />
					</Avatar>
					<div>
						<Typography variant="body2">{name}</Typography>
						{row.paymentMethod.last4 ? (
							<Typography color="text.secondary" variant="body2">
								**** {row.paymentMethod.last4}
							</Typography>
						) : null}
					</div>
				</Stack>
			);
		},
		name: "Payment Method",
		width: "200px",
	},
	{
		formatter: (row) => (
			<Stack spacing={0.5}>
				<Typography variant="subtitle2">{dayjs(row.transactionDate).format("MMM D, YYYY")}</Typography>
				<Typography color="text.secondary" variant="caption">
					{dayjs(row.transactionDate).format("hh:mm A")}
				</Typography>
			</Stack>
		),
		name: "Date",
		width: "170px",
	},
	{
		formatter: (row) => {
			// Defensive normalization (handles enum-style strings like 'receiptstatus.completed')
			const raw = (row.status || "").toString().trim().toLowerCase();
			const key = raw.includes(".") ? raw.split(".").pop() : raw;
			const mapping = {
				pending: {
					label: "Pending",
					icon: <ClockIcon color="var(--mui-palette-warning-main)" weight="fill" />,
					color: "warning",
				},
				processing: {
					label: "Processing",
					icon: <ClockIcon color="var(--mui-palette-warning-main)" weight="fill" />,
					color: "warning",
				},
				completed: {
					label: "Completed",
					icon: <CheckCircleIcon color="var(--mui-palette-success-main)" weight="fill" />,
					color: "success",
				},
				canceled: {
					label: "Canceled",
					icon: <XCircleIcon color="var(--mui-palette-error-main)" weight="fill" />,
					color: "error",
				},
				rejected: {
					label: "Rejected",
					icon: <MinusIcon color="var(--mui-palette-error-main)" />,
					color: "error",
				},
				failed: {
					label: "Failed",
					icon: <XCircleIcon color="var(--mui-palette-error-main)" weight="fill" />,
					color: "error",
				},
			};
			const mapped = key ? mapping[key] : null;
			const label = mapped?.label || key || "—";
			const icon = mapped?.icon || null;
			const color = mapped?.color || (mapped ? "default" : "default");
			return <Chip icon={icon} label={label} size="small" color={color} variant="outlined" />;
		},
		name: "Status",
		width: "120px",
	},
	{
		formatter: (row) => {
			return (
				<Select
					variant="outlined"
					size="small"
					value={row.category || ""}
					onChange={(e) => handleCategoryChange(row.id, e.target.value || undefined, row)}
					displayEmpty
					fullWidth
					MenuProps={{ disableScrollLock: true }}
					// Prevent row click selection toggling when interacting with dropdown
					onClick={(e) => e.stopPropagation()}
					onFocus={(e) => e.stopPropagation()}
					style={{ minWidth: 180 }}
				>
					<MenuItem value="">
						<em>Unassigned</em>
					</MenuItem>
					{Object.keys(RECEIPT_CATEGORY_MAP).map((cat) => (
						<MenuItem key={cat} value={cat}>
							{cat}
						</MenuItem>
					))}
				</Select>
			);
		},
		name: "Category",
		width: "220px",
	},
	{
		formatter: (row) => (
			<Stack direction="row" spacing={1} sx={{ justifyContent: "flex-end" }}>
				<IconButton
					component={RouterLink}
					href={paths.dashboard.receiptsPreview(row.id)}
					onClick={(e) => {
						if (previewCache.get(row.id)?.loaded) return;
						if (prewarmPreview) {
							e.preventDefault();
							prewarmPreview(row.id).then(() => {
								globalThis.history.pushState({}, "", paths.dashboard.receiptsPreview(row.id));
							});
						}
					}}
				>
					<EyeIcon />
				</IconButton>
			</Stack>
		),
		name: "Open",
		hideName: true,
		width: "80px",
		align: "right",
	},
];

export function ReceiptsTable({ rows, prewarmPreview, token: tokenProp }) {
	const tokenAuto = useTokenOnce();
	const token = tokenProp === undefined ? tokenAuto : tokenProp;
	// Map of optimistic category overrides keyed by receipt id
	const [categoryOverrides, setCategoryOverrides] = React.useState({});

	// Track receipts that have been deleted (so we skip PATCH attempts / rollbacks cleanly)
	const deletedIdsRef = React.useRef(new Set());
	React.useEffect(() => {
		function onDeleted(e) {
			const id = e?.detail?.id;
			if (id == null) return;
			deletedIdsRef.current.add(id);
			// If we still show a category override for a deleted id, remove it to prevent stale UI
			setCategoryOverrides((prev) => {
				if (!(id in prev)) return prev;
				const clone = { ...prev };
				delete clone[id];
				return clone;
			});
		}
		globalThis.addEventListener("receipt:deleted", onDeleted);
		return () => globalThis.removeEventListener("receipt:deleted", onDeleted);
	}, []);

	const mapped = React.useMemo(
		() =>
			rows.map((r) => {
				const base = toDisplayRow(r);
				// Extract current category (may be string or array) from extracted_data
				let existingCategory;
				try {
					const rawCat = r?.extracted_data?.category;
					if (Array.isArray(rawCat)) existingCategory = rawCat[0];
					else if (typeof rawCat === "string") existingCategory = rawCat;
				} catch {
					/* swallow */
				}
				return { ...base, category: categoryOverrides[r.id] ?? existingCategory, __orig: r };
			}),
		[rows, categoryOverrides]
	);
	const { selected, deselectAll, deselectOne, selectAll, selectOne } = useReceiptsSelection();
	// Normalize selection (context provides a Set)
	const selectedCount = React.useMemo(() => (selected ? (selected.size ?? (selected.length || 0)) : 0), [selected]);

	const handleCategoryChange = React.useCallback(
		async (id, newCategory, row) => {
			if (deletedIdsRef.current.has(id)) {
				// Skip interaction on a deleted receipt
				toast.error("Receipt was deleted – category not updated");
				return;
			}
			// optimistic override + stats event
			setCategoryOverrides((prev) => ({ ...prev, [id]: newCategory }));
			const prevCategory = row.category || null;
			const amount = typeof row.totalAmount === "number" ? row.totalAmount : 0;
			try {
				globalThis.dispatchEvent(
					new CustomEvent("receipt:category", {
						detail: { id, category: newCategory || null, prevCategory, amount },
					})
				);
			} catch {
				/* ignore */
			}

			// Build updated extracted_data preserving existing fields
			const orig = row?.__orig || rows.find((r) => r.id === id);
			const existing = (orig && typeof orig.extracted_data === "object" && orig.extracted_data) || {};
			const updated = { ...existing };
			if (newCategory) updated.category = newCategory;
			else delete updated.category;
			if (!token) return; // cannot persist without auth token

			const rollback = (reason) => {
				setCategoryOverrides((prev) => {
					const clone = { ...prev };
					if (existing?.category) clone[id] = existing.category;
					else delete clone[id];
					return clone;
				});
				try {
					globalThis.dispatchEvent(
						new CustomEvent("receipt:category", {
							detail: { id, category: existing?.category || null, prevCategory: newCategory || null, amount },
						})
					);
				} catch {
					/* ignore */
				}
				if (reason) toast.error(reason);
			};

			try {
				const res = await fetch(`/api/receipts/${id}`, {
					method: "PATCH",
					headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
					body: JSON.stringify({ extracted_data: updated }),
				});
				if (!res.ok) {
					if (res.status === 404) {
						deletedIdsRef.current.add(id);
						rollback("Receipt no longer exists (deleted)");
						return;
					}
					const text = await res.text().catch(() => "");
					rollback(text || `Failed to update category (${res.status})`);
					return;
				}
			} catch (error) {
				rollback("Network error updating category");
				console.warn("Failed to update category", error);
			}
		},
		[token, rows]
	);

	return (
		<React.Fragment>
			{selectedCount > 0 ? (
				<Box
					sx={{
						mb: 1,
						px: 2,
						py: 1,
						border: "1px solid var(--mui-palette-divider)",
						borderRadius: 1,
						bgcolor: "background.paper",
						display: "flex",
						alignItems: "center",
						justifyContent: "space-between",
					}}
				>
					<Typography variant="body2">{selectedCount} selected</Typography>
					<Stack direction="row" spacing={1}>
						<Button size="small" onClick={deselectAll} variant="outlined">
							Clear
						</Button>
						{/* Delete action removed */}
					</Stack>
				</Box>
			) : null}
			<DataTable
				columns={columns(token, prewarmPreview, handleCategoryChange)}
				onDeselectAll={deselectAll}
				onDeselectOne={(_, row) => {
					deselectOne(row.id);
				}}
				onSelectAll={selectAll}
				onSelectOne={(_, row) => {
					selectOne(row.id);
				}}
				rows={mapped}
				selectable
				selected={selected}
			/>
			{mapped.length === 0 ? (
				<Box sx={{ p: 3 }}>
					<Typography color="text.secondary" sx={{ textAlign: "center" }} variant="body2">
						No receipts found
					</Typography>
				</Box>
			) : null}
			{/* Delete dialogs removed */}
		</React.Fragment>
	);
}
