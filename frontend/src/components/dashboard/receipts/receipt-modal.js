"use client";

import * as React from "react";
import RouterLink from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@clerk/nextjs";
import Avatar from "@mui/material/Avatar";
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
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import { CheckCircleIcon } from "@phosphor-icons/react/dist/ssr/CheckCircle";
// Removed image zoom icon import since preview is gone
// import { MagnifyingGlassPlus } from "@phosphor-icons/react/dist/ssr/MagnifyingGlassPlus";
import { PencilSimpleIcon } from "@phosphor-icons/react/dist/ssr/PencilSimple";
import { XIcon } from "@phosphor-icons/react/dist/ssr/X";

import { paths } from "@/paths";
import { dayjs } from "@/lib/dayjs";
import { parseAmount } from "@/lib/parse-amount";
import { useReceiptDetails } from "@/hooks/use-receipt-details";
import { PropertyItem } from "@/components/core/property-item";
import { PropertyList } from "@/components/core/property-list";
import { LineItemsTable } from "@/components/dashboard/order/line-items-table";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Numeric helpers
function safeNum(v, def = 0) {
	if (typeof v === "number") return Number.isFinite(v) ? v : def;
	if (typeof v === "string") {
		const trimmed = v.trim();
		if (!trimmed) return def;
		const n = Number(trimmed);
		return Number.isFinite(n) ? n : def;
	}
	return def;
}

export function ReceiptModal({ open, receiptId, receipt: providedReceipt, previewSrc: prefetchedPreview }) {
	const router = useRouter();
	const { getToken } = useAuth();

	// Centralized receipt + preview data via custom hook
	const {
		receipt,
		loading,
		refreshing,
		error,
		// image/preview removed
	} = useReceiptDetails({ open, receiptId, providedReceipt, prefetchedPreview });
	// Minimal: fetch a signed download URL and expose a single button to open the receipt
	const [downloadHref, setDownloadHref] = React.useState(null);
	const [imageError, setImageError] = React.useState(false);

	// Provide legacy-shaped state objects for downstream rendering logic (minimize diff)
	const detailState = React.useMemo(
		() => ({ data: receipt, loading, refreshing, error }),
		[receipt, loading, refreshing, error]
	);

	const handleClose = React.useCallback(() => {
		router.push(paths.dashboard.receipts);
	}, [router]);

	// Fetch signed download URL on open/id change
	React.useEffect(() => {
		let cancelled = false;
		async function run() {
			if (!open || !receiptId) return;
			try {
				let token = null;
				try {
					token = await getToken?.();
				} catch {
					/* optional token fetch failed */
				}
				const res = await fetch(`${API_URL}/receipts/${encodeURIComponent(receiptId)}/download_url`, {
					headers: token ? { Authorization: `Bearer ${token}` } : undefined,
					cache: "no-store",
				});
				if (!res.ok) return;
				const data = await res.json();
				if (!cancelled && data?.url) {
					const abs = data.url.startsWith("http") ? data.url : `${API_URL}${data.url}`;
					setDownloadHref(abs);
				}
			} catch {
				if (!cancelled) setDownloadHref(null);
			}
		}
		setDownloadHref(null);
		setImageError(false);
		run();
		return () => {
			cancelled = true;
		};
	}, [open, receiptId, getToken]);

	// Only display receipt details if they belong to the currently requested receiptId
	// Normalize id types to string to avoid mismatch causing hidden details
	const displayedReceipt = React.useMemo(() => {
		if (!receipt || !receiptId) return null;
		return String(receipt.id) === String(receiptId) ? receipt : null;
	}, [receipt, receiptId]);
	const ed =
		displayedReceipt && typeof displayedReceipt.extracted_data === "object" ? displayedReceipt.extracted_data : {};
	const merchant = (ed && (ed.merchant ?? ed.vendor ?? ed.merchant_name)) || "—";
	// Address can arrive as a string, structured object, or array. Normalize to a display string.
	function formatAddress(addr) {
		if (!addr) return null;
		if (typeof addr === "string") {
			const trimmed = addr.trim();
			return trimmed || null;
		}
		if (Array.isArray(addr)) {
			return formatAddress(addr.filter(Boolean).join(", "));
		}
		if (typeof addr === "object") {
			// Common field variants
			const fieldsOrder = [
				"line1",
				"line2",
				"street1",
				"street2",
				"street",
				"street_address",
				"streetAddress",
				"address1",
				"address2",
				"city",
				"town",
				"state",
				"province",
				"region",
				"postal_code",
				"postalCode",
				"zip",
				"zip_code",
				"country",
				"country_code",
				"countryCode",
				"raw",
			];
			const parts = [];
			const seen = new Set();
			for (const key of fieldsOrder) {
				if (key in addr) {
					let v = addr[key];
					if (v && typeof v === "object") {
						// Nested object: attempt flatten of its primitive values
						const nestedVals = Object.values(v).filter((x) => typeof x === "string" && x.trim());
						if (nestedVals.length > 0) v = nestedVals.join(" ");
					}
					if (typeof v === "string") {
						const cleaned = v.trim();
						if (cleaned && !seen.has(cleaned.toLowerCase())) {
							seen.add(cleaned.toLowerCase());
							parts.push(cleaned);
						}
					}
				}
			}
			// If no ordered fields produced output, fall back to primitive stringifiable values.
			if (parts.length === 0) {
				const fallback = Object.values(addr)
					.filter((v) => typeof v === "string" && v.trim())
					.map((v) => v.trim());
				const unique = [];
				for (const f of fallback) {
					if (!unique.includes(f)) unique.push(f);
				}
				if (unique.length > 0) return unique.join(", ");
			}
			return parts.length > 0 ? parts.join(", ") : null;
		}
		return null;
	}
	const rawAddress = ed && (ed.address || ed.location || ed.merchant_address || null);
	const address = formatAddress(rawAddress);
	const totalRaw = ed && (ed.total ?? ed.amount_total ?? ed.amount);
	const totalParsed = parseAmount(totalRaw);
	const shippingRaw = ed && (ed.shipping ?? ed.delivery ?? null);
	const receivingRaw = ed && (ed.receiving ?? ed.handling ?? null);
	const shippingAmount = parseAmount(shippingRaw) || 0;
	const receivingAmount = parseAmount(receivingRaw) || 0;
	const taxAmount = parseAmount(ed?.tax) || 0;
	const explicitSubtotal = parseAmount(ed?.subtotal) || 0;
	// (moved subtotal/discount inference below after lineItems & total definitions)

	// Audit decision indicators
	const auditDecision =
		displayedReceipt && typeof displayedReceipt.audit_decision === "object" ? displayedReceipt.audit_decision : null;
	const needsAudit = Boolean(auditDecision?.needs_audit);
	const auditMathError = Boolean(auditDecision?.math_error);
	const amountOverLimit = Boolean(auditDecision?.amount_over_limit);
	const lineItems = Array.isArray(ed?.items)
		? ed.items.map((it, idx) => {
				const unitRaw = it.unit_price ?? it.price ?? it.unit ?? it.rate;
				const qtyRaw = it.qty ?? it.quantity ?? 1;
				const lineTotalRaw = it.total ?? it.amount ?? (unitRaw && qtyRaw ? unitRaw : 0);
				const quantity = safeNum(qtyRaw, 1);
				const unitAmount = parseAmount(unitRaw);
				const totalAmount = parseAmount(lineTotalRaw) || (unitAmount && quantity ? unitAmount * quantity : 0);
				return {
					id: String(idx + 1).padStart(3, "0"),
					product: it.name || it.description || `Item ${idx + 1}`,
					image: "/assets/product-1.png",
					quantity,
					currency: "USD",
					unitAmount,
					totalAmount,
				};
			})
		: [];

	// If header total parsed as 0 but line items have sum, use sum as fallback.
	const lineItemsSum = lineItems.reduce((acc, li) => acc + (Number.isFinite(li.totalAmount) ? li.totalAmount : 0), 0);
	const total = totalParsed > 0 ? totalParsed : lineItemsSum;

	// Attempt to infer subtotal if not explicitly provided (depends on lineItemsSum & total)
	let inferredSubtotal = explicitSubtotal;
	if (!inferredSubtotal) {
		if (lineItemsSum > 0) {
			const candidate = lineItemsSum - (taxAmount + shippingAmount + receivingAmount);
			if (candidate > 0) inferredSubtotal = candidate;
		}
		if (!inferredSubtotal && total > 0) {
			const candidate2 = total - (taxAmount + shippingAmount + receivingAmount);
			if (candidate2 > 0) inferredSubtotal = candidate2;
		}
	}
	// Discount: explicit or derived difference between components and provided total
	const explicitDiscount = parseAmount(ed?.discount) || parseAmount(ed?.discounts) || parseAmount(ed?.saving) || 0;
	let derivedDiscount = 0;
	if (total > 0) {
		const sumComponents = inferredSubtotal + taxAmount + shippingAmount + receivingAmount;
		if (sumComponents > 0) {
			const diff = sumComponents - total;
			if (diff > 0.02) derivedDiscount = diff; // treat positive difference as discount
		}
	}
	const discountAmount = explicitDiscount || derivedDiscount;
	// Math validation client-side (mirrors backend logic w/ discount consideration)
	let mathMismatch = false;
	if (inferredSubtotal > 0 && total > 0) {
		const expected = inferredSubtotal + taxAmount + shippingAmount + receivingAmount - discountAmount;
		if (Math.abs(expected - total) > 0.02) mathMismatch = true;
	}

	// Derive payment method (brand + last4) similar to receipts table
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
		if (type) {
			paymentMethod = { type, brand: rawBrand, last4 };
		}
	}
	const paymentMapping = {
		mastercard: { name: "Mastercard", logo: "/assets/payment-method-1.png" },
		visa: { name: "Visa", logo: "/assets/payment-method-2.png" },
		amex: { name: "American Express", logo: "/assets/payment-method-3.png" },
		applepay: { name: "Apple Pay", logo: "/assets/payment-method-4.png" },
		googlepay: { name: "Google Pay", logo: "/assets/payment-method-5.png" },
	};
	const paymentDisplay = paymentMethod ? (
		<Stack direction="row" spacing={2} sx={{ alignItems: "center" }}>
			{paymentMapping[paymentMethod.type]?.logo ? (
				<Avatar sx={{ bgcolor: "var(--mui-palette-background-paper)", boxShadow: "var(--mui-shadows-8)" }}>
					<Box
						component="img"
						src={paymentMapping[paymentMethod.type].logo}
						alt={paymentMapping[paymentMethod.type].name}
						sx={{ borderRadius: "50px", height: "auto", width: 35 }}
					/>
				</Avatar>
			) : null}
			<Box>
				<Typography variant="body2">
					{paymentMapping[paymentMethod.type]?.name || paymentMethod.brand || "Unknown"}
				</Typography>
				{paymentMethod.last4 ? (
					<Typography color="text.secondary" variant="body2">
						**** {paymentMethod.last4}
					</Typography>
				) : null}
			</Box>
		</Stack>
	) : (
		"—"
	);

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
					<Typography variant="h6">{displayedReceipt ? `RCP-${displayedReceipt.id}` : "Receipt"}</Typography>
					<IconButton onClick={handleClose}>
						<XIcon />
					</IconButton>
				</Stack>
				<Stack spacing={3} sx={{ flex: "1 1 auto", overflow: "auto" }}>
					{detailState.loading && !detailState.data ? (
						<Typography color="text.secondary" variant="body2">
							Loading…
						</Typography>
					) : detailState.error ? (
						<Typography color="error.main" variant="body2">
							{String(detailState.error)}
						</Typography>
					) : null}
					<Stack spacing={3}>
						<Stack direction="row" spacing={3} sx={{ alignItems: "center", justifyContent: "space-between" }}>
							<Typography variant="h6">Details</Typography>
							<Button
								color="secondary"
								component={RouterLink}
								href={paths.dashboard.receiptsDetails(String(displayedReceipt?.id || ""))}
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
										value: address ? <Typography variant="subtitle2">{address}</Typography> : "—",
									},
									{
										key: "Date",
										value: displayedReceipt ? dayjs(displayedReceipt.created_at).format("MMMM D, YYYY hh:mm A") : "—",
									},
									{
										key: "Status",
										value: (
											<Chip
												icon={<CheckCircleIcon color="var(--mui-palette-success-main)" weight="fill" />}
												label={
													(displayedReceipt?.status || "").toString().charAt(0).toUpperCase() +
													(displayedReceipt?.status || "").toString().slice(1)
												}
												size="small"
												variant="outlined"
											/>
										),
									},
									{
										key: "Audit",
										value: needsAudit ? (
											<Stack direction="row" spacing={1} sx={{ flexWrap: "wrap" }}>
												{auditMathError && (
													<Tooltip title="Math mismatch detected between components and total">
														<Chip color="error" size="small" label="Math Error" />
													</Tooltip>
												)}
												{amountOverLimit && <Chip color="warning" size="small" label="Over Limit" />}
											</Stack>
										) : (
											<Typography variant="body2" color="text.secondary">
												None
											</Typography>
										),
									},
									{ key: "Payment Method", value: paymentDisplay },
									{ key: "Filename", value: displayedReceipt?.filename || "—" },
								].map((item) => (
									<PropertyItem key={item.key} name={item.key} value={item.value} />
								))}
							</PropertyList>
						</Card>

            {/* Inline receipt display */}
				<Card sx={{ borderRadius: 1 }} variant="outlined">
					<Box sx={{ p: 2 }}>
						<Box
							sx={{
								position: "relative",
								width: "100%",
								height: 520,
								border: "1px solid",
								borderColor: "divider",
								borderRadius: 1,
								overflow: "hidden",
								bgcolor: "background.default",
							}}
						>
							{downloadHref ? (
								imageError ? (
									<iframe src={downloadHref} title="Receipt" style={{ width: "100%", height: "100%", border: 0 }} />
								) : (
									<Box
										component="img"
										src={downloadHref}
										alt="Receipt"
										onError={() => setImageError(true)}
										sx={{ position: "absolute", inset: 0, width: "100%", height: "100%", objectFit: "contain" }}
									/>
								)
							) : (
								<Box
									sx={{
										position: "absolute",
										inset: 0,
										display: "flex",
										alignItems: "center",
										justifyContent: "center",
									}}
								>
									<Typography variant="body2" color="text.secondary">
										Preparing receipt…
									</Typography>
								</Box>
							)}
						</Box>
					</Box>
				</Card>



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
											{inferredSubtotal
												? new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(
														inferredSubtotal
													)
												: "-"}
										</Typography>
									</Stack>
									<Stack direction="row" spacing={3} sx={{ justifyContent: "space-between" }}>
										<Typography variant="body2">Discount</Typography>
										<Typography variant="body2" color={discountAmount ? "success.main" : undefined}>
											{discountAmount
												? `- ${new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(discountAmount)}`
												: "-"}
										</Typography>
									</Stack>
									<Stack direction="row" spacing={3} sx={{ justifyContent: "space-between" }}>
										<Typography variant="body2">Shipping</Typography>
										<Typography variant="body2">
											{shippingAmount
												? new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(shippingAmount)
												: "-"}
										</Typography>
									</Stack>
									<Stack direction="row" spacing={3} sx={{ justifyContent: "space-between" }}>
										<Typography variant="body2">Receiving</Typography>
										<Typography variant="body2">
											{receivingAmount
												? new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(receivingAmount)
												: "-"}
										</Typography>
									</Stack>
									<Stack direction="row" spacing={3} sx={{ justifyContent: "space-between" }}>
										<Typography variant="body2">Taxes</Typography>
										<Typography variant="body2">
											{taxAmount
												? new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(taxAmount)
												: "-"}
										</Typography>
									</Stack>
									<Stack direction="row" spacing={3} sx={{ justifyContent: "space-between" }}>
										<Typography variant="subtitle1">Total</Typography>
										<Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
											<Typography variant="subtitle1">
												{new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(total)}
											</Typography>
											{(mathMismatch || auditMathError) && (
												<Tooltip title="The sum of components does not match total (see math)">
													<Chip color="error" size="small" label="Mismatch" />
												</Tooltip>
											)}
										</Stack>
									</Stack>
									{displayedReceipt?.status === "failed" && (
										<Box sx={{ pt: 1, display: "flex", justifyContent: "flex-end" }}>
											<Button
												size="small"
												variant="outlined"
												onClick={async () => {
													try {
														let token = null;
														try {
															token = await getToken?.();
														} catch {
															/* silent token fetch failure */
														}
														await fetch(`${API_URL}/receipts/${encodeURIComponent(displayedReceipt.id)}/reprocess`, {
															method: "POST",
															headers: token ? { Authorization: `Bearer ${token}` } : undefined,
														});
													} catch {
														/* silent reprocess failure */
													}
												}}
											>
												Reprocess
											</Button>
										</Box>
									)}
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
