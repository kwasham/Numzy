"use client";

import * as React from "react";
import RouterLink from "next/link";
import Avatar from "@mui/material/Avatar";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import IconButton from "@mui/material/IconButton";
import LinearProgress from "@mui/material/LinearProgress";
import Link from "@mui/material/Link";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import { CheckCircleIcon } from "@phosphor-icons/react/dist/ssr/CheckCircle";
import { ClockIcon } from "@phosphor-icons/react/dist/ssr/Clock";
import { EyeIcon } from "@phosphor-icons/react/dist/ssr/Eye";
import { MinusIcon } from "@phosphor-icons/react/dist/ssr/Minus";
import { XCircleIcon } from "@phosphor-icons/react/dist/ssr/XCircle";

import { paths } from "@/paths";
import { dayjs } from "@/lib/dayjs";
import { parseAmount } from "@/lib/parse-amount";
import { DataTable } from "@/components/core/data-table";

import { useReceiptsSelection } from "./receipts-selection-context";

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

const columns = [
	{
		formatter: (row) => (
			<Stack direction="row" spacing={2} sx={{ alignItems: "center" }}>
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
			const { label, icon, color } = mapping[row.status] ?? { label: row.status, icon: null, color: "default" };

			return <Chip icon={icon} label={label} size="small" color={color} variant="outlined" />;
		},
		name: "Status",
		width: "100px",
	},
	{
		formatter: (row) => (
			<IconButton component={RouterLink} href={paths.dashboard.receiptsPreview(row.id)}>
				<EyeIcon />
			</IconButton>
		),
		name: "Actions",
		hideName: true,
		width: "100px",
		align: "right",
	},
];

export function ReceiptsTable({ rows }) {
	const mapped = React.useMemo(() => rows.map((r) => toDisplayRow(r)), [rows]);
	const { selected, deselectAll, deselectOne, selectAll, selectOne } = useReceiptsSelection();

	return (
		<React.Fragment>
			<DataTable
				columns={columns}
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
		</React.Fragment>
	);
}
