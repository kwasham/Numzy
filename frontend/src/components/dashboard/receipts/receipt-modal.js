"use client";

import * as React from "react";
import RouterLink from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@clerk/nextjs";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import Chip from "@mui/material/Chip";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import Divider from "@mui/material/Divider";
import IconButton from "@mui/material/IconButton";
import Link from "@mui/material/Link";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import { CheckCircleIcon } from "@phosphor-icons/react/dist/ssr/CheckCircle";
import { PencilSimpleIcon } from "@phosphor-icons/react/dist/ssr/PencilSimple";
import { XIcon } from "@phosphor-icons/react/dist/ssr/X";

import { paths } from "@/paths";
import { dayjs } from "@/lib/dayjs";
import { PropertyItem } from "@/components/core/property-item";
import { PropertyList } from "@/components/core/property-list";
import { LineItemsTable } from "@/components/dashboard/order/line-items-table";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function ReceiptModal({ open, receiptId }) {
	const router = useRouter();
	const { getToken } = useAuth();

	const [loading, setLoading] = React.useState(false);
	const [error, setError] = React.useState(null);
	const [receipt, setReceipt] = React.useState(null);
	const [downloadUrl, setDownloadUrl] = React.useState(null);
	const [thumbUrl, setThumbUrl] = React.useState(null);

	const handleClose = React.useCallback(() => {
		router.push(paths.dashboard.receipts);
	}, [router]);

	React.useEffect(() => {
		let active = true;
		async function run() {
			if (!open || !receiptId) return;
			setLoading(true);
			setError(null);
			try {
				let token = null;
				try {
					token = await getToken?.();
				} catch (error_) {
					// ignore auth token errors in dev
					console.debug("getToken error", error_);
				}
				const auth = token ? { Authorization: `Bearer ${token}` } : undefined;
				const res = await fetch(`${API_URL}/receipts/${encodeURIComponent(receiptId)}`, { headers: auth });
				if (!res.ok) throw new Error(`Failed to load receipt (${res.status})`);
				const data = await res.json();
				if (!active) return;
				setReceipt(data);
				// Fetch signed thumbnail URL for preview (preferred)
				try {
					const tres = await fetch(`${API_URL}/receipts/${encodeURIComponent(receiptId)}/thumbnail_url`, {
						headers: auth,
					});
					if (tres.ok) {
						const { url } = await tres.json();
						setThumbUrl(`${API_URL}${url}`);
					}
				} catch (error_) {
					console.debug("thumbnail_url error", error_);
				}
				// Fallback: signed download URL
				try {
					const dres = await fetch(`${API_URL}/receipts/${encodeURIComponent(receiptId)}/download_url`, {
						headers: auth,
					});
					if (dres.ok) {
						const { url } = await dres.json();
						setDownloadUrl(`${API_URL}${url}`);
					}
				} catch (error_) {
					console.debug("download_url error", error_);
				}
			} catch (error_) {
				if (!active) return;
				setError(error_?.message || "Failed to load");
			} finally {
				if (active) setLoading(false);
			}
		}
		run();
		return () => {
			active = false;
		};
	}, [open, receiptId, getToken]);

	const ed = receipt && typeof receipt.extracted_data === "object" ? receipt.extracted_data : {};
	const merchant = (ed && (ed.merchant ?? ed.vendor ?? ed.merchant_name)) || "—";
	const address = ed && (ed.address || ed.location || null);
	const totalRaw = ed && (ed.total ?? ed.amount_total ?? ed.amount);
	const total =
		typeof totalRaw === "number"
			? totalRaw
			: typeof totalRaw === "string"
				? Number(totalRaw.replaceAll(/[^0-9.-]/g, ""))
				: 0;
	const lineItems = Array.isArray(ed?.items)
		? ed.items.map((it, idx) => ({
				id: String(idx + 1).padStart(3, "0"),
				product: it.name || it.description || `Item ${idx + 1}`,
				image: "/assets/product-1.png",
				quantity: Number(it.qty || it.quantity || 1),
				currency: "USD",
				unitAmount: Number(it.unit_price || it.price || 0),
				totalAmount: Number(it.total || it.amount || 0),
			}))
		: [];

	const payment = ed?.payment_method || null;
	const paymentLabel = payment
		? [payment.type, payment.brand && `(${payment.brand}${payment.last4 ? ` •••• ${payment.last4}` : ""})`]
				.filter(Boolean)
				.join(" ")
		: "—";

	const previewSrc = thumbUrl || downloadUrl || null;

	return (
		<Dialog
			maxWidth="sm"
			onClose={handleClose}
			open={open}
			sx={{
				"& .MuiDialog-container": { justifyContent: "flex-end" },
				"& .MuiDialog-paper": { height: "100%", width: "100%" },
			}}
		>
			<DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, minHeight: 0, overflow: "hidden" }}>
				<Stack direction="row" sx={{ alignItems: "center", flex: "0 0 auto", justifyContent: "space-between" }}>
					<Typography variant="h6">{receipt ? `RCP-${receipt.id}` : "Receipt"}</Typography>
					<IconButton onClick={handleClose}>
						<XIcon />
					</IconButton>
				</Stack>
				<Stack spacing={3} sx={{ flex: "1 1 auto", overflow: "auto" }}>
					{loading ? (
						<Typography color="text.secondary" variant="body2">
							Loading…
						</Typography>
					) : error ? (
						<Typography color="error.main" variant="body2">
							{String(error)}
						</Typography>
					) : null}
					<Stack spacing={3}>
						<Stack direction="row" spacing={3} sx={{ alignItems: "center", justifyContent: "space-between" }}>
							<Typography variant="h6">Details</Typography>
							<Button
								color="secondary"
								component={RouterLink}
								href={paths.dashboard.receiptsDetails(String(receipt?.id || ""))}
								startIcon={<PencilSimpleIcon />}
							>
								Edit
							</Button>
						</Stack>
						<Card sx={{ borderRadius: 1 }} variant="outlined">
							<PropertyList divider={<Divider />} sx={{ "--PropertyItem-padding": "12px 24px" }}>
								{[
									{ key: "Merchant", value: <Link variant="subtitle2">{merchant}</Link> },
									{
										key: "Address",
										value: address ? <Typography variant="subtitle2">{String(address)}</Typography> : "—",
									},
									{
										key: "Date",
										value: receipt ? dayjs(receipt.created_at).format("MMMM D, YYYY hh:mm A") : "—",
									},
									{
										key: "Status",
										value: (
											<Chip
												icon={<CheckCircleIcon color="var(--mui-palette-success-main)" weight="fill" />}
												label={
													(receipt?.status || "").toString().charAt(0).toUpperCase() +
													(receipt?.status || "").toString().slice(1)
												}
												size="small"
												variant="outlined"
											/>
										),
									},
									{ key: "Payment Method", value: paymentLabel },
									{ key: "Filename", value: receipt?.filename || "—" },
								].map((item) => (
									<PropertyItem key={item.key} name={item.key} value={item.value} />
								))}
							</PropertyList>
						</Card>
						{previewSrc ? (
							<Card sx={{ borderRadius: 1 }} variant="outlined">
								<Box sx={{ p: 2 }}>
									<Box
										component="img"
										src={previewSrc}
										alt="Receipt preview"
										sx={{ width: "100%", height: "auto", borderRadius: 1 }}
									/>
								</Box>
							</Card>
						) : null}
					</Stack>
					<Stack spacing={3}>
						<Typography variant="h6">Line items</Typography>
						<Card sx={{ borderRadius: 1 }} variant="outlined">
							<Box sx={{ overflowX: "auto" }}>
								<LineItemsTable rows={lineItems} />
							</Box>
							<Divider />
							<Box sx={{ display: "flex", justifyContent: "flex-end", p: 3 }}>
								<Stack spacing={2} sx={{ width: "300px", maxWidth: "100%" }}>
									<Stack direction="row" spacing={3} sx={{ justifyContent: "space-between" }}>
										<Typography variant="body2">Subtotal</Typography>
										<Typography variant="body2">
											{new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(total || 0)}
										</Typography>
									</Stack>
									<Stack direction="row" spacing={3} sx={{ justifyContent: "space-between" }}>
										<Typography variant="body2">Discount</Typography>
										<Typography variant="body2">-</Typography>
									</Stack>
									<Stack direction="row" spacing={3} sx={{ justifyContent: "space-between" }}>
										<Typography variant="body2">Shipping</Typography>
										<Typography variant="body2">-</Typography>
									</Stack>
									<Stack direction="row" spacing={3} sx={{ justifyContent: "space-between" }}>
										<Typography variant="body2">Taxes</Typography>
										<Typography variant="body2">-</Typography>
									</Stack>
									<Stack direction="row" spacing={3} sx={{ justifyContent: "space-between" }}>
										<Typography variant="subtitle1">Total</Typography>
										<Typography variant="subtitle1">
											{new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(total || 0)}
										</Typography>
									</Stack>
								</Stack>
							</Box>
						</Card>
					</Stack>
				</Stack>
			</DialogContent>
		</Dialog>
	);
}

export default ReceiptModal;
