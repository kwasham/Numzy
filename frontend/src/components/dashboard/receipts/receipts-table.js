"use client";

import { useAuth } from "@clerk/nextjs";
import Avatar from "@mui/material/Avatar";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Checkbox from "@mui/material/Checkbox";
import Chip from "@mui/material/Chip";
import Divider from "@mui/material/Divider";
import Icon from "@mui/material/Icon";
import IconButton from "@mui/material/IconButton";
import LinearProgress from "@mui/material/LinearProgress";
import Link from "@mui/material/Link";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import { ArrowClockwiseIcon } from "@phosphor-icons/react/dist/ssr/ArrowClockwise";
import { CheckCircleIcon } from "@phosphor-icons/react/dist/ssr/CheckCircle";
import { ClockIcon } from "@phosphor-icons/react/dist/ssr/Clock";
import { DownloadSimpleIcon } from "@phosphor-icons/react/dist/ssr/DownloadSimple";
import { EyeIcon } from "@phosphor-icons/react/dist/ssr/Eye";
import { MinusIcon } from "@phosphor-icons/react/dist/ssr/Minus";
import { XCircleIcon } from "@phosphor-icons/react/dist/ssr/XCircle";
import RouterLink from "next/link";
import * as React from "react";
import { toast } from "sonner";

import { DataTable } from "@/components/core/data-table";
import { RECEIPT_CATEGORY_MAP } from "@/components/dashboard/receipts/categories";
import {
    markThumbFailure,
    previewCache,
    setPreview,
    shouldAttemptThumb,
} from "@/components/dashboard/receipts/receipt-cache";
import { dayjs } from "@/lib/dayjs";
import { parseAmount } from "@/lib/parse-amount";
import { paths } from "@/paths";

import { useReceiptsSelection } from "./receipts-selection-context";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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

function formatCurrency(value, currency = "USD") {
	if (value == null || Number.isNaN(value)) return "—";
	try {
		return new Intl.NumberFormat("en-US", { style: "currency", currency }).format(value);
	} catch {
		return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(value);
	}
}

function toDisplayRow(r) {
	const ed = r.extracted_data && typeof r.extracted_data === "object" ? r.extracted_data : {};
	const merchant = ed.merchant ?? ed.vendor ?? ed.merchant_name ?? "—";
	const totalRaw = ed.total ?? ed.amount_total ?? ed.amount;
	const totalAmount = parseAmount(totalRaw);
	let transactionDate = new Date(r.created_at);
	const timeRaw = ed.time || ed.transaction_time || ed.transactionDate || null;
	if (timeRaw) {
		const candidate = dayjs(timeRaw);
		if (candidate.isValid()) transactionDate = candidate.toDate();
		else {
			const alt = new Date(timeRaw);
			if (!Number.isNaN(alt.getTime())) transactionDate = alt;
		}
	}
	const pmSource = ed.payment_method || ed.payment || ed.card || null;
	let paymentMethod = null;
	if (pmSource && typeof pmSource === "object") {
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
		if (type) paymentMethod = { type, brand: rawBrand, last4 };
	}
	const extractionProgressRaw = Number(r.extraction_progress);
	const auditProgressRaw = Number(r.audit_progress);
	const extractionProgress = Number.isFinite(extractionProgressRaw)
		? Math.max(0, Math.min(100, extractionProgressRaw))
		: null;
	const auditProgress = Number.isFinite(auditProgressRaw) ? Math.max(0, Math.min(100, auditProgressRaw)) : null;
	let progressPercent = null;
	if (typeof extractionProgress === "number" || typeof auditProgress === "number") {
		const parts = [];
		if (typeof extractionProgress === "number") parts.push(extractionProgress);
		if (typeof auditProgress === "number") parts.push(auditProgress);
		if (parts.length > 0) {
			const avg = parts.reduce((acc, val) => acc + val, 0) / parts.length;
			progressPercent = Math.round(avg);
		}
	}
	return {
		id: r.id,
		merchantName: merchant,
		createdAt: new Date(r.created_at),
		transactionDate,
		lineItems: 1,
		paymentMethod,
		currency: "USD",
		totalAmount,
		formattedTotal: formatCurrency(totalAmount, "USD"),
		status: r.status,
		extractionProgress: extractionProgress ?? 0,
		auditProgress: auditProgress ?? 0,
		progressPercent,
		customer: { name: merchant, avatar: undefined, email: undefined },
	};
}

const STATUS_META = {
	pending: {
		label: "Pending",
		color: "warning",
		icon: <ClockIcon color="var(--mui-palette-warning-main)" weight="fill" />,
	},
	processing: {
		label: "Processing",
		color: "warning",
		icon: <ClockIcon color="var(--mui-palette-warning-main)" weight="fill" />,
	},
	completed: {
		label: "Completed",
		color: "success",
		icon: <CheckCircleIcon color="var(--mui-palette-success-main)" weight="fill" />,
	},
	canceled: {
		label: "Canceled",
		color: "error",
		icon: <XCircleIcon color="var(--mui-palette-error-main)" weight="fill" />,
	},
	rejected: {
		label: "Rejected",
		color: "error",
		icon: <MinusIcon color="var(--mui-palette-error-main)" />,
	},
	failed: {
		label: "Failed",
		color: "error",
		icon: <XCircleIcon color="var(--mui-palette-error-main)" weight="fill" />,
	},
};

function getStatusMeta(statusRaw) {
	const key = (statusRaw || "").toString().trim().toLowerCase();
	const normalized = key.includes(".") ? key.split(".").pop() : key;
	return STATUS_META[normalized] || {
		label: normalized || "—",
		color: "default",
		icon: null,
	};
}

function BulkActionBar({ busy, count, onClear, onDownload, onReprocess }) {
	return (
		<Card
			elevation={0}
			sx={{
				border: "1px solid var(--mui-palette-divider)",
				mb: 2,
				position: { xs: "sticky", md: "static" },
				top: { xs: 16, md: "auto" },
				zIndex: 1,
			}}
		>
			<CardContent sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", py: 1.5 }}>
				<Typography variant="body2">{count} selected</Typography>
				<Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
					<Button size="small" startIcon={<DownloadSimpleIcon />} onClick={onDownload} disabled={busy === "download"}>
						Download
					</Button>
					<Button size="small" startIcon={<ArrowClockwiseIcon />} onClick={onReprocess} disabled={busy === "reprocess"}>
						Reprocess
					</Button>
					<Divider flexItem orientation="vertical" sx={{ mx: 1 }} />
					<Button size="small" variant="outlined" onClick={onClear}>
						Clear
					</Button>
				</Stack>
			</CardContent>
		</Card>
	);
}

function MobileReceiptCard({ onCategoryChange, onOpen, onPrefetch, row, selected, toggleSelected }) {
	const statusMeta = getStatusMeta(row.status);
	return (
		<Card variant="outlined">
			<CardContent sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
				<Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
					<Checkbox
						size="small"
						checked={selected}
						onChange={() => toggleSelected(row.id, selected)}
						inputProps={{ "aria-label": "Select receipt" }}
					/>
					<Stack spacing={0.5} sx={{ flex: 1 }}>
						<Link
							color="text.primary"
							component={RouterLink}
							href={paths.dashboard.receiptsPreview(row.id)}
							variant="subtitle2"
							onClick={() => onOpen(row.id)}
							onFocus={() => onPrefetch(row.id)}
						>
							{row.merchantName}
						</Link>
						<Typography variant="body2" color="text.secondary">
							{row.formattedTotal}
						</Typography>
						{["pending", "processing"].includes((row.status || "").toLowerCase()) && (
							<Box sx={{ mt: 0.5 }}>
								<LinearProgress
									variant={typeof row.progressPercent === "number" ? "determinate" : "indeterminate"}
									value={typeof row.progressPercent === "number" ? row.progressPercent : 0}
									sx={{ height: 6, borderRadius: 3 }}
								/>
								{typeof row.progressPercent === "number" ? (
									<Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: "block" }}>
										{row.progressPercent}% complete
									</Typography>
								) : null}
							</Box>
						)}
					</Stack>
				</Stack>
				<Stack direction="row" spacing={1} sx={{ alignItems: "center", flexWrap: "wrap" }}>
					<Chip icon={statusMeta.icon} label={statusMeta.label} size="small" color={statusMeta.color} variant="outlined" />
					<Typography variant="caption" color="text.secondary">
						{dayjs(row.transactionDate).format("MMM D, YYYY • hh:mm A")}
					</Typography>
				</Stack>
				{row.paymentMethod ? (
					<Stack direction="row" spacing={2} sx={{ alignItems: "center" }}>
						{(() => {
							const mapping = {
								mastercard: { name: "Mastercard", logo: "/assets/payment-method-1.png" },
								visa: { name: "Visa", logo: "/assets/payment-method-2.png" },
								amex: { name: "American Express", logo: "/assets/payment-method-3.png" },
								applepay: { name: "Apple Pay", logo: "/assets/payment-method-4.png" },
								googlepay: { name: "Google Pay", logo: "/assets/payment-method-5.png" },
							};
							const pm = mapping[row.paymentMethod.type];
							if (!pm?.logo) return null;
							return (
								<Avatar sx={{ bgcolor: "var(--mui-palette-background-paper)", boxShadow: "var(--mui-shadows-8)" }}>
									<Box component="img" src={pm.logo} alt={pm.name} sx={{ borderRadius: "50px", width: 35 }} />
								</Avatar>
							);
						})()}
						<Stack spacing={0.25}>
							<Typography variant="body2">
								{(() => {
									const mapping = {
										mastercard: "Mastercard",
										visa: "Visa",
										amex: "American Express",
										applepay: "Apple Pay",
										googlepay: "Google Pay",
									};
									return mapping[row.paymentMethod.type] || row.paymentMethod.brand || "Payment";
								})()}
							</Typography>
							{row.paymentMethod.last4 ? (
								<Typography color="text.secondary" variant="body2">
									**** {row.paymentMethod.last4}
								</Typography>
							) : null}
						</Stack>
					</Stack>
				) : null}
				<Select
					variant="outlined"
					size="small"
					value={row.category || ""}
					onChange={(event) => onCategoryChange(row.id, event.target.value || undefined, row)}
					displayEmpty
					fullWidth
					MenuProps={{ disableScrollLock: true }}
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
				<Button
					size="small"
					startIcon={<EyeIcon />}
					component={RouterLink}
					href={paths.dashboard.receiptsPreview(row.id)}
					onClick={() => onOpen(row.id)}
					variant="text"
					sx={{ alignSelf: "flex-start" }}
				>
					Open receipt
				</Button>
			</CardContent>
		</Card>
	);
}

export function ReceiptsTable({ rows, prewarmPreview, token: tokenProp }) {
	const tokenAuto = useTokenOnce();
	const token = tokenProp === undefined ? tokenAuto : tokenProp;
	const [categoryOverrides, setCategoryOverrides] = React.useState({});
	const deletedIdsRef = React.useRef(new Set());
	const [bulkAction, setBulkAction] = React.useState(null);
	const [sortState, setSortState] = React.useState({ orderBy: "createdAt", order: "desc" });
	React.useEffect(() => {
		function onDeleted(e) {
			const id = e?.detail?.id;
			if (id == null) return;
			deletedIdsRef.current.add(id);
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
				let existingCategory;
				try {
					const rawCat = r?.extracted_data?.category;
					if (Array.isArray(rawCat)) existingCategory = rawCat[0];
					else if (typeof rawCat === "string") existingCategory = rawCat;
				} catch {
					/* ignore malformed extracted_data.category */
				}
				return { ...base, category: categoryOverrides[r.id] ?? existingCategory, __orig: r };
			}),
		[rows, categoryOverrides]
	);

	const { selected, deselectAll, deselectOne, selectAll, selectOne } = useReceiptsSelection();
	const selectedCount = React.useMemo(() => (selected ? (selected.size ?? (selected.length || 0)) : 0), [selected]);
	const selectedIds = React.useMemo(() => (selected ? Array.from(selected) : []), [selected]);

	const handleCategoryChange = React.useCallback(
		async (id, newCategory, row) => {
			if (deletedIdsRef.current.has(id)) {
				toast.error("Receipt was deleted – category not updated");
				return;
			}
			setCategoryOverrides((prev) => ({ ...prev, [id]: newCategory }));
			const prevCategory = row.category || null;
			const amount = typeof row.totalAmount === "number" ? row.totalAmount : 0;
			try {
				globalThis.dispatchEvent(
					new CustomEvent("receipt:category", { detail: { id, category: newCategory || null, prevCategory, amount } })
				);
			} catch {
				/* ignore dispatch error */
			}
			const orig = row?.__orig || rows.find((item) => item.id === id);
			const existing = (orig && typeof orig.extracted_data === "object" && orig.extracted_data) || {};
			const updated = { ...existing };
			if (newCategory) updated.category = newCategory;
			else delete updated.category;
			if (!token) return;
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
					/* ignore rollback dispatch */
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

	const prefetchThumb = React.useCallback(
		(id) => {
			if (!token) return;
			if (previewCache.get(id) || previewCache.get(String(id))) return;
			if (!shouldAttemptThumb(id)) return;
			const thumb = `/api/receipts/${encodeURIComponent(id)}/thumb`;
			try {
				const img = new Image();
				img.addEventListener("load", () => setPreview(id, thumb, true));
				img.addEventListener("error", () => markThumbFailure(id));
				img.src = `${thumb}${thumb.includes("?") ? "&" : "?"}pre=1`;
			} catch {
				/* ignore thumbnail prefetch failure */
			}
		},
		[token]
	);

	const handleOpen = React.useCallback(
		(id) => {
			if (prewarmPreview && !previewCache.get(id)) {
				try {
					prewarmPreview(id);
				} catch {
					/* ignore */
				}
			}
			if (process.env.NEXT_PUBLIC_DEBUG_RECEIPTS === "true") {
				console.debug("[receipts-table] navigate to preview", id);
			}
		},
		[prewarmPreview]
	);

	const sortedRows = React.useMemo(() => {
		const arr = [...mapped];
		const { orderBy, order } = sortState || {};
		if (!orderBy) return arr;
		const dir = order === "asc" ? 1 : -1;
		arr.sort((a, b) => {
			switch (orderBy) {
				case "merchantName": {
					const aVal = (a.merchantName || "").toLowerCase();
					const bVal = (b.merchantName || "").toLowerCase();
					if (aVal === bVal) return 0;
					return aVal > bVal ? dir : -dir;
				}
				case "totalAmount": {
					const aVal = Number.isFinite(a.totalAmount) ? a.totalAmount : -Infinity;
					const bVal = Number.isFinite(b.totalAmount) ? b.totalAmount : -Infinity;
					if (aVal === bVal) return 0;
					return aVal > bVal ? dir : -dir;
				}
				case "createdAt":
				default: {
					const aTime = a.createdAt?.getTime?.() || 0;
					const bTime = b.createdAt?.getTime?.() || 0;
					if (aTime === bTime) return 0;
					return aTime > bTime ? dir : -dir;
				}
			}
		});
		return arr;
	}, [mapped, sortState]);

	const columns = React.useMemo(
		() => [
			{
				key: "merchant",
				name: "Merchant",
				width: "260px",
				sortable: true,
				sortKey: "merchantName",
				formatter: (row) => {
					const statusMeta = getStatusMeta(row.status);
					return (
						<Stack spacing={1} onMouseEnter={() => prefetchThumb(row.id)} onFocus={() => prefetchThumb(row.id)}>
							<Stack direction="row" spacing={1} sx={{ alignItems: "center", minWidth: 0 }}>
								<Link
									color="text.primary"
									component={RouterLink}
									href={paths.dashboard.receiptsPreview(row.id)}
									variant="subtitle2"
									sx={{ display: "inline-flex", minWidth: 0 }}
									onClick={() => handleOpen(row.id)}
								>
									<Typography variant="subtitle2" sx={{ overflow: "hidden", textOverflow: "ellipsis" }}>
										{row.merchantName}
									</Typography>
								</Link>
								<Chip icon={statusMeta.icon} label={statusMeta.label} size="small" color={statusMeta.color} variant="outlined" />
							</Stack>
							<Typography variant="body2" color="text.secondary">
								{row.formattedTotal}
							</Typography>
							{["pending", "processing"].includes((row.status || "").toLowerCase()) && (
								<Box sx={{ maxWidth: 180 }}>
									<LinearProgress
										variant={typeof row.progressPercent === "number" ? "determinate" : "indeterminate"}
										value={typeof row.progressPercent === "number" ? row.progressPercent : 0}
										sx={{ height: 6, borderRadius: 3 }}
									/>
									{typeof row.progressPercent === "number" ? (
										<Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: "block" }}>
											{row.progressPercent}% complete
										</Typography>
									) : null}
								</Box>
							)}
						</Stack>
					);
				},
			},
			{
				key: "date",
				name: "Date",
				width: "160px",
				sortable: true,
				sortKey: "createdAt",
				formatter: (row) => (
					<Stack spacing={0.5}>
						<Typography variant="subtitle2">{dayjs(row.transactionDate).format("MMM D, YYYY")}</Typography>
						<Typography color="text.secondary" variant="caption">
							{dayjs(row.transactionDate).format("hh:mm A")}
						</Typography>
					</Stack>
				),
			},
			{
				key: "amount",
				name: "Amount",
				width: "120px",
				sortable: true,
				sortKey: "totalAmount",
				align: "right",
				formatter: (row) => (
					<Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
						{row.formattedTotal}
					</Typography>
				),
			},
			{
				key: "payment",
				name: "Payment",
				width: "220px",
				formatter: (row) => {
					if (!row.paymentMethod) return <Typography variant="body2">—</Typography>;
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
							{logo ? (
								<Avatar sx={{ bgcolor: "var(--mui-palette-background-paper)", boxShadow: "var(--mui-shadows-8)" }}>
									<Box component="img" src={logo} alt={name} sx={{ borderRadius: "50px", width: 35 }} />
								</Avatar>
							) : (
								<Icon>credit_card</Icon>
							)}
							<Stack spacing={0.25}>
								<Typography variant="body2">{name}</Typography>
								{row.paymentMethod.last4 ? (
									<Typography color="text.secondary" variant="body2">
										**** {row.paymentMethod.last4}
									</Typography>
								) : null}
							</Stack>
						</Stack>
					);
				},
			},
			{
				key: "category",
				name: "Category",
				width: "220px",
				formatter: (row) => (
					<Select
						variant="outlined"
						size="small"
						value={row.category || ""}
						onChange={(event) => handleCategoryChange(row.id, event.target.value || undefined, row)}
						displayEmpty
						fullWidth
						MenuProps={{ disableScrollLock: true }}
						onClick={(event) => event.stopPropagation()}
						onFocus={(event) => event.stopPropagation()}
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
				),
			},
			{
				key: "actions",
				name: "",
				hideName: true,
				width: "72px",
				align: "right",
				formatter: (row) => (
					<IconButton component={RouterLink} href={paths.dashboard.receiptsPreview(row.id)} onClick={() => handleOpen(row.id)}>
						<EyeIcon />
					</IconButton>
				),
			},
		],
		[handleCategoryChange, handleOpen, prefetchThumb]
	);

	const handleSortChange = React.useCallback((next) => {
		setSortState({ order: next.order, orderBy: next.orderBy });
	}, []);

	const handleBulkDownload = React.useCallback(async () => {
		if (!selectedIds.length) return;
		setBulkAction("download");
		try {
			await Promise.all(
				selectedIds.map(async (id) => {
					const res = await fetch(`${API_URL}/receipts/${encodeURIComponent(id)}/download_url`, {
						headers: token ? { Authorization: `Bearer ${token}` } : undefined,
						cache: "no-store",
					});
					if (!res.ok) throw new Error(`Failed to request download (${res.status})`);
					const data = await res.json();
					if (!data?.url) return;
					const href = data.url.startsWith("http") ? data.url : `${API_URL}${data.url}`;
					const anchor = document.createElement("a");
					anchor.href = href;
					anchor.target = "_blank";
					anchor.rel = "noopener";
					anchor.click();
				})
			);
			toast.success(`Started download for ${selectedIds.length} receipt${selectedIds.length > 1 ? "s" : ""}`);
		} catch (error) {
			toast.error("Unable to download selected receipts");
			console.warn("Bulk download failed", error);
		} finally {
			setBulkAction(null);
		}
	}, [selectedIds, token]);

	const handleBulkReprocess = React.useCallback(async () => {
		if (!selectedIds.length) return;
		setBulkAction("reprocess");
		try {
			await Promise.all(
				selectedIds.map(async (id) => {
					try {
						await fetch(`${API_URL}/receipts/${encodeURIComponent(id)}/reprocess`, {
							method: "POST",
							headers: token ? { Authorization: `Bearer ${token}` } : undefined,
						});
					} catch (error) {
						console.warn("Failed to reprocess receipt", id, error);
					}
				})
			);
			toast.success(`Triggered reprocess for ${selectedIds.length} receipt${selectedIds.length > 1 ? "s" : ""}`);
		} catch (error) {
			toast.error("Unable to reprocess selected receipts");
			console.warn("Bulk reprocess failed", error);
		} finally {
			setBulkAction(null);
		}
	}, [selectedIds, token]);

	const toggleCardSelection = React.useCallback(
		(id, currentlySelected) => {
			if (currentlySelected) deselectOne(id);
			else selectOne(id);
		},
		[deselectOne, selectOne]
	);

	return (
		<React.Fragment>
			{selectedCount > 0 ? (
				<BulkActionBar
					busy={bulkAction}
					count={selectedCount}
					onClear={deselectAll}
					onDownload={handleBulkDownload}
					onReprocess={handleBulkReprocess}
				/>
			) : null}
			<Box sx={{ display: { xs: "none", md: "block" } }}>
				<DataTable
					columns={columns}
					rows={sortedRows}
					selectable
					selected={selected}
					onDeselectAll={deselectAll}
					onDeselectOne={(_, row) => deselectOne(row.id)}
					onSelectAll={selectAll}
					onSelectOne={(_, row) => selectOne(row.id)}
					sortState={sortState}
					onSortChange={handleSortChange}
				/>
				{sortedRows.length === 0 ? (
					<Box sx={{ p: 3 }}>
						<Typography color="text.secondary" sx={{ textAlign: "center" }} variant="body2">
							No receipts found
						</Typography>
					</Box>
				) : null}
			</Box>
			<Stack spacing={2} sx={{ display: { xs: "flex", md: "none" } }}>
				{sortedRows.length === 0 ? (
					<Card variant="outlined">
						<CardContent>
							<Typography color="text.secondary" sx={{ textAlign: "center" }} variant="body2">
								No receipts found
							</Typography>
						</CardContent>
					</Card>
				) : (
					sortedRows.map((row) => (
						<MobileReceiptCard
							key={row.id}
							row={row}
							selected={selected?.has(row.id)}
							toggleSelected={toggleCardSelection}
							onCategoryChange={handleCategoryChange}
							onOpen={handleOpen}
							onPrefetch={prefetchThumb}
						/>
					))
				)}
			</Stack>
		</React.Fragment>
	);
}

export default ReceiptsTable;




// function useTokenOnce() {
// 	const { getToken } = useAuth();
// 	const [token, setToken] = React.useState();
// 	React.useEffect(() => {
// 		let cancelled = false;
// 		(async () => {
// 			try {
// 				const t = await getToken?.();
// 				if (!cancelled) setToken(t || "");
// 			} catch {
// 				if (!cancelled) setToken("");
// 			}
// 		})();
// 		return () => {
// 			cancelled = true;
// 		};
// 	}, [getToken]);
// 	return token;
// }

// function toDisplayRow(r) {
// 	const ed = r.extracted_data && typeof r.extracted_data === "object" ? r.extracted_data : {};
// 	const merchant = ed.merchant ?? ed.vendor ?? ed.merchant_name ?? "—";
// 	const totalRaw = ed.total ?? ed.amount_total ?? ed.amount;
// 	const totalAmount = parseAmount(totalRaw);
// 	let transactionDate = new Date(r.created_at);
// 	const timeRaw = ed.time || ed.transaction_time || ed.transactionDate || null;
// 	if (timeRaw) {
// 		const candidate = dayjs(timeRaw);
// 		if (candidate.isValid()) transactionDate = candidate.toDate();
// 		else {
// 			const alt = new Date(timeRaw);
// 			if (!Number.isNaN(alt.getTime())) transactionDate = alt;
// 		}
// 	}
// 	const pmSource = ed.payment_method || ed.payment || ed.card || null;
// 	let paymentMethod = null;
// 	if (pmSource && typeof pmSource === "object") {
// 		const rawBrand =
// 			pmSource.brand || pmSource.type || pmSource.card_brand || pmSource.scheme || pmSource.network || "";
// 		const norm = String(rawBrand)
// 			.toLowerCase()
// 			.replaceAll(/[^a-z0-9]/g, "");
// 		const brandMap = {
// 			visa: "visa",
// 			mastercard: "mastercard",
// 			mc: "mastercard",
// 			americanexpress: "amex",
// 			amex: "amex",
// 			applepay: "applepay",
// 			apple: "applepay",
// 			googlepay: "googlepay",
// 			google: "googlepay",
// 		};
// 		const type = brandMap[norm] || norm || null;
// 		const last4 =
// 			pmSource.last4 ||
// 			pmSource.card_last4 ||
// 			(pmSource.number && String(pmSource.number).slice(-4)) ||
// 			(pmSource.card_number && String(pmSource.card_number).slice(-4)) ||
// 			null;
// 		if (type) paymentMethod = { type, brand: rawBrand, last4 };
// 	}
// 	const extractionProgressRaw = Number(r.extraction_progress);
// 	const auditProgressRaw = Number(r.audit_progress);
// 	const extractionProgress = Number.isFinite(extractionProgressRaw)
// 		? Math.max(0, Math.min(100, extractionProgressRaw))
// 		: null;
// 	const auditProgress = Number.isFinite(auditProgressRaw) ? Math.max(0, Math.min(100, auditProgressRaw)) : null;
// 	let progressPercent = null;
// 	if (typeof extractionProgress === "number" || typeof auditProgress === "number") {
// 		const parts = [];
// 		if (typeof extractionProgress === "number") parts.push(extractionProgress);
// 		if (typeof auditProgress === "number") parts.push(auditProgress);
// 		if (parts.length > 0) {
// 			const avg = parts.reduce((acc, val) => acc + val, 0) / parts.length;
// 			progressPercent = Math.round(avg);
// 		}
// 	}
// 	return {
// 		id: r.id,
// 		createdAt: new Date(r.created_at),
// 		transactionDate,
// 		lineItems: 1,
// 		paymentMethod,
// 		currency: "USD",
// 		totalAmount,
// 		status: r.status,
// 		extractionProgress: extractionProgress ?? 0,
// 		auditProgress: auditProgress ?? 0,
// 		progressPercent,
// 		customer: { name: merchant, avatar: undefined, email: undefined },
// 	};
// }

// const columns = (token, prewarmPreview, handleCategoryChange) => [
// 	{
// 		formatter: (row) => (
// 			<Stack
// 				direction="row"
// 				spacing={2}
// 				sx={{ alignItems: "center" }}
// 				onMouseEnter={() => {
// 					if (!token) return;
// 					if (previewCache.get(row.id) || previewCache.get(String(row.id))) return;
// 					if (!shouldAttemptThumb(row.id)) return;
// 					const thumb = `/api/receipts/${encodeURIComponent(row.id)}/thumb`;
// 					try {
// 						const img = new Image();
// 						img.addEventListener("load", () => setPreview(row.id, thumb, true));
// 						img.addEventListener("error", () => markThumbFailure(row.id));
// 						img.src = `${thumb}${thumb.includes("?") ? "&" : "?"}pre=1`;
// 					} catch {
// 						// ignore thumbnail prefetch failure
// 					}
// 				}}
// 			>
// 				<Box
// 					sx={{
// 						bgcolor: "var(--mui-palette-background-level1)",
// 						borderRadius: 1.5,
// 						flex: "0 0 auto",
// 						p: "4px 8px",
// 						textAlign: "center",
// 					}}
// 				>
// 					<Typography variant="caption">{dayjs(row.createdAt).format("MMM").toUpperCase()}</Typography>
// 					<Typography variant="h6">{dayjs(row.createdAt).format("D")}</Typography>
// 				</Box>
// 				<div style={{ minWidth: 160 }}>
// 					<Link
// 						color="text.primary"
// 						component={RouterLink}
// 						href={paths.dashboard.receiptsPreview(row.id)}
// 						sx={{ cursor: "pointer" }}
// 						onClick={() => {
// 							// Always navigate immediately; prewarm in background for faster modal image.
// 							if (prewarmPreview && !previewCache.get(row.id)) {
// 								try {
// 									prewarmPreview(row.id);
// 								} catch {
// 									/* ignore */
// 								}
// 							}
// 							if (process.env.NEXT_PUBLIC_DEBUG_RECEIPTS === "true") {
// 								console.debug("[receipts-table] navigate to preview", row.id);
// 							}
// 							// Let the default link navigation occur (href already set)
// 						}}
// 						onFocus={() => {
// 							if (previewCache.get(row.id) || previewCache.get(String(row.id))) return;
// 							if (!shouldAttemptThumb(row.id)) return;
// 							const thumb = `/api/receipts/${encodeURIComponent(row.id)}/thumb`;
// 							try {
// 								const img = new Image();
// 								img.addEventListener("load", () => setPreview(row.id, thumb, true));
// 								img.addEventListener("error", () => markThumbFailure(row.id));
// 								img.src = `${thumb}${thumb.includes("?") ? "&" : "?"}pre=1`;
// 							} catch {
// 								// ignore prefetch focus error
// 							}
// 						}}
// 						variant="subtitle2"
// 					>
// 						{row.customer.name}
// 					</Link>
// 					<Typography variant="body2" color="text.secondary" sx={{ lineHeight: 1.3 }}>
// 						{row.totalAmount != null && !Number.isNaN(row.totalAmount)
// 							? new Intl.NumberFormat("en-US", { style: "currency", currency: row.currency || "USD" }).format(
// 									row.totalAmount
// 								)
// 							: "—"}
// 					</Typography>
// 					{["pending", "processing"].includes((row.status || "").toLowerCase()) && (
// 						<Box sx={{ mt: 0.5 }}>
// 							<LinearProgress
// 								variant={typeof row.progressPercent === "number" ? "determinate" : "indeterminate"}
// 								value={typeof row.progressPercent === "number" ? row.progressPercent : 0}
// 								sx={{ height: 6, borderRadius: 3, width: 140, bgcolor: "background.default" }}
// 							/>
// 							{typeof row.progressPercent === "number" ? (
// 								<Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: "block" }}>
// 									{row.progressPercent}% complete
// 								</Typography>
// 							) : null}
// 						</Box>
// 					)}
// 				</div>
// 			</Stack>
// 		),
// 		name: "Receipt",
// 		width: "250px",
// 	},
// 	{
// 		formatter: (row) => {
// 			if (!row.paymentMethod) return null;
// 			const mapping = {
// 				mastercard: { name: "Mastercard", logo: "/assets/payment-method-1.png" },
// 				visa: { name: "Visa", logo: "/assets/payment-method-2.png" },
// 				amex: { name: "American Express", logo: "/assets/payment-method-3.png" },
// 				applepay: { name: "Apple Pay", logo: "/assets/payment-method-4.png" },
// 				googlepay: { name: "Google Pay", logo: "/assets/payment-method-5.png" },
// 			};
// 			const { name, logo } = mapping[row.paymentMethod.type] ?? { name: "Unknown", logo: null };
// 			return (
// 				<Stack direction="row" spacing={2} sx={{ alignItems: "center" }}>
// 					<Avatar sx={{ bgcolor: "var(--mui-palette-background-paper)", boxShadow: "var(--mui-shadows-8)" }}>
// 						<Box component="img" src={logo} sx={{ borderRadius: "50px", height: "auto", width: "35px" }} />
// 					</Avatar>
// 					<div>
// 						<Typography variant="body2">{name}</Typography>
// 						{row.paymentMethod.last4 ? (
// 							<Typography color="text.secondary" variant="body2">
// 								**** {row.paymentMethod.last4}
// 							</Typography>
// 						) : null}
// 					</div>
// 				</Stack>
// 			);
// 		},
// 		name: "Payment Method",
// 		width: "200px",
// 	},
// 	{
// 		formatter: (row) => (
// 			<Stack spacing={0.5}>
// 				<Typography variant="subtitle2">{dayjs(row.transactionDate).format("MMM D, YYYY")}</Typography>
// 				<Typography color="text.secondary" variant="caption">
// 					{dayjs(row.transactionDate).format("hh:mm A")}
// 				</Typography>
// 			</Stack>
// 		),
// 		name: "Date",
// 		width: "170px",
// 	},
// 	{
// 		formatter: (row) => {
// 			const raw = (row.status || "").toString().trim().toLowerCase();
// 			const key = raw.includes(".") ? raw.split(".").pop() : raw;
// 			const mapping = {
// 				pending: {
// 					label: "Pending",
// 					icon: <ClockIcon color="var(--mui-palette-warning-main)" weight="fill" />,
// 					color: "warning",
// 				},
// 				processing: {
// 					label: "Processing",
// 					icon: <ClockIcon color="var(--mui-palette-warning-main)" weight="fill" />,
// 					color: "warning",
// 				},
// 				completed: {
// 					label: "Completed",
// 					icon: <CheckCircleIcon color="var(--mui-palette-success-main)" weight="fill" />,
// 					color: "success",
// 				},
// 				canceled: {
// 					label: "Canceled",
// 					icon: <XCircleIcon color="var(--mui-palette-error-main)" weight="fill" />,
// 					color: "error",
// 				},
// 				rejected: { label: "Rejected", icon: <MinusIcon color="var(--mui-palette-error-main)" />, color: "error" },
// 				failed: {
// 					label: "Failed",
// 					icon: <XCircleIcon color="var(--mui-palette-error-main)" weight="fill" />,
// 					color: "error",
// 				},
// 			};
// 			const mapped = key ? mapping[key] : null;
// 			const label = mapped?.label || key || "—";
// 			const icon = mapped?.icon || null;
// 			const color = mapped?.color || (mapped ? "default" : "default");
// 			return <Chip icon={icon} label={label} size="small" color={color} variant="outlined" />;
// 		},
// 		name: "Status",
// 		width: "120px",
// 	},
// 	{
// 		formatter: (row) => (
// 			<Select
// 				variant="outlined"
// 				size="small"
// 				value={row.category || ""}
// 				onChange={(e) => handleCategoryChange(row.id, e.target.value || undefined, row)}
// 				displayEmpty
// 				fullWidth
// 				MenuProps={{ disableScrollLock: true }}
// 				onClick={(e) => e.stopPropagation()}
// 				onFocus={(e) => e.stopPropagation()}
// 				style={{ minWidth: 180 }}
// 			>
// 				<MenuItem value="">
// 					<em>Unassigned</em>
// 				</MenuItem>
// 				{Object.keys(RECEIPT_CATEGORY_MAP).map((cat) => (
// 					<MenuItem key={cat} value={cat}>
// 						{cat}
// 					</MenuItem>
// 				))}
// 			</Select>
// 		),
// 		name: "Category",
// 		width: "220px",
// 	},
// 	{
// 		formatter: (row) => (
// 			<Stack direction="row" spacing={1} sx={{ justifyContent: "flex-end" }}>
// 				<IconButton
// 					component={RouterLink}
// 					href={paths.dashboard.receiptsPreview(row.id)}
// 					onClick={() => {
// 						if (prewarmPreview && !previewCache.get(row.id)) {
// 							try {
// 								prewarmPreview(row.id);
// 							} catch {
// 								/* ignore */
// 							}
// 						}
// 						if (process.env.NEXT_PUBLIC_DEBUG_RECEIPTS === "true") {
// 							console.debug("[receipts-table] icon navigate to preview", row.id);
// 						}
// 					}}
// 				>
// 					<EyeIcon />
// 				</IconButton>
// 			</Stack>
// 		),
// 		name: "Open",
// 		hideName: true,
// 		width: "80px",
// 		align: "right",
// 	},
// ];

// export function ReceiptsTable({ rows, prewarmPreview, token: tokenProp }) {
// 	const tokenAuto = useTokenOnce();
// 	const token = tokenProp === undefined ? tokenAuto : tokenProp;
// 	const [categoryOverrides, setCategoryOverrides] = React.useState({});
// 	const deletedIdsRef = React.useRef(new Set());
// 	React.useEffect(() => {
// 		function onDeleted(e) {
// 			const id = e?.detail?.id;
// 			if (id == null) return;
// 			deletedIdsRef.current.add(id);
// 			setCategoryOverrides((prev) => {
// 				if (!(id in prev)) return prev;
// 				const clone = { ...prev };
// 				delete clone[id];
// 				return clone;
// 			});
// 		}
// 		globalThis.addEventListener("receipt:deleted", onDeleted);
// 		return () => globalThis.removeEventListener("receipt:deleted", onDeleted);
// 	}, []);

// 	const mapped = React.useMemo(
// 		() =>
// 			rows.map((r) => {
// 				const base = toDisplayRow(r);
// 				let existingCategory;
// 				try {
// 					const rawCat = r?.extracted_data?.category;
// 					if (Array.isArray(rawCat)) existingCategory = rawCat[0];
// 					else if (typeof rawCat === "string") existingCategory = rawCat;
// 				} catch {
// 					// ignore malformed extracted_data.category
// 				}
// 				return { ...base, category: categoryOverrides[r.id] ?? existingCategory, __orig: r };
// 			}),
// 		[rows, categoryOverrides]
// 	);

// 	const { selected, deselectAll, deselectOne, selectAll, selectOne } = useReceiptsSelection();
// 	const selectedCount = React.useMemo(() => (selected ? (selected.size ?? (selected.length || 0)) : 0), [selected]);

// 	const handleCategoryChange = React.useCallback(
// 		async (id, newCategory, row) => {
// 			if (deletedIdsRef.current.has(id)) {
// 				toast.error("Receipt was deleted – category not updated");
// 				return;
// 			}
// 			setCategoryOverrides((prev) => ({ ...prev, [id]: newCategory }));
// 			const prevCategory = row.category || null;
// 			const amount = typeof row.totalAmount === "number" ? row.totalAmount : 0;
// 			try {
// 				globalThis.dispatchEvent(
// 					new CustomEvent("receipt:category", { detail: { id, category: newCategory || null, prevCategory, amount } })
// 				);
// 			} catch {
// 				// ignore dispatch error
// 			}
// 			const orig = row?.__orig || rows.find((r) => r.id === id);
// 			const existing = (orig && typeof orig.extracted_data === "object" && orig.extracted_data) || {};
// 			const updated = { ...existing };
// 			if (newCategory) updated.category = newCategory;
// 			else delete updated.category;
// 			if (!token) return;
// 			const rollback = (reason) => {
// 				setCategoryOverrides((prev) => {
// 					const clone = { ...prev };
// 					if (existing?.category) clone[id] = existing.category;
// 					else delete clone[id];
// 					return clone;
// 				});
// 				try {
// 					globalThis.dispatchEvent(
// 						new CustomEvent("receipt:category", {
// 							detail: { id, category: existing?.category || null, prevCategory: newCategory || null, amount },
// 						})
// 					);
// 				} catch {
// 					// ignore dispatch rollback error
// 				}
// 				if (reason) toast.error(reason);
// 			};
// 			try {
// 				const res = await fetch(`/api/receipts/${id}`, {
// 					method: "PATCH",
// 					headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
// 					body: JSON.stringify({ extracted_data: updated }),
// 				});
// 				if (!res.ok) {
// 					if (res.status === 404) {
// 						deletedIdsRef.current.add(id);
// 						rollback("Receipt no longer exists (deleted)");
// 						return;
// 					}
// 					const text = await res.text().catch(() => "");
// 					rollback(text || `Failed to update category (${res.status})`);
// 					return;
// 				}
// 			} catch (error) {
// 				rollback("Network error updating category");
// 				console.warn("Failed to update category", error);
// 			}
// 		},
// 		[token, rows]
// 	);

// 	return (
// 		<React.Fragment>
// 			{selectedCount > 0 ? (
// 				<Box
// 					sx={{
// 						mb: 1,
// 						px: 2,
// 						py: 1,
// 						border: "1px solid var(--mui-palette-divider)",
// 						borderRadius: 1,
// 						bgcolor: "background.paper",
// 						display: "flex",
// 						alignItems: "center",
// 						justifyContent: "space-between",
// 					}}
// 				>
// 					<Typography variant="body2">{selectedCount} selected</Typography>
// 					<Stack direction="row" spacing={1}>
// 						<Button size="small" onClick={deselectAll} variant="outlined">
// 							Clear
// 						</Button>
// 					</Stack>
// 				</Box>
// 			) : null}
// 			<DataTable
// 				columns={columns(token, prewarmPreview, handleCategoryChange)}
// 				onDeselectAll={deselectAll}
// 				onDeselectOne={(_, row) => {
// 					deselectOne(row.id);
// 				}}
// 				onSelectAll={selectAll}
// 				onSelectOne={(_, row) => {
// 					selectOne(row.id);
// 				}}
// 				rows={mapped}
// 				selectable
// 				selected={selected}
// 			/>
// 			{mapped.length === 0 ? (
// 				<Box sx={{ p: 3 }}>
// 					<Typography color="text.secondary" sx={{ textAlign: "center" }} variant="body2">
// 						No receipts found
// 					</Typography>
// 				</Box>
// 			) : null}
// 		</React.Fragment>
// 	);
// }

// export default ReceiptsTable;
