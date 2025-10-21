"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@clerk/nextjs";
import { Box } from "@mui/material";

import { ReceiptLike, useReceiptDetails } from "@/hooks/use-receipt-details";
import {
	ActionNav,
	DataExtractedTable,
	ExtractedSummaryCard,
	ImageToolbar,
	LeftCategories,
	LabeledCategoriesCard,
	ReceiptViewer,
	TopBar,
} from "./detail-sections";

interface Props {
	receiptId: string;
	providedReceipt?: ReceiptLike | null; // raw receipt object from server prefetch (optional)
	prefetchedPreview?: string | null; // optional pre-fetched preview URL
}
const BRAND_NAME = "Numzy";
const capitalize = (s: string) => (s ? s[0].toUpperCase() + s.slice(1) : s);
const arraysEqual = (a: string[], b: string[]) => a.length === b.length && a.every((v, i) => v === b[i]);

export default function ReceiptDetailClient({ receiptId, providedReceipt = null, prefetchedPreview = null }: Props) {
	const {
		detail,
		receipt,
		loading,
		previewSrc,
		downloadUrl,
		updateCategories,
		updatingCategories,
		categoriesError,
	} = useReceiptDetails({
		open: true,
		receiptId,
		providedReceipt: providedReceipt || null,
		prefetchedPreview: prefetchedPreview || null,
	});
	const router = useRouter();
	const { getToken } = useAuth();
	const initialCategories = detail?.categories ? [...detail.categories] : [];
	const [categoriesState, setCategoriesState] = useState<{ value: string[]; dirty: boolean }>({
		value: initialCategories,
		dirty: false,
	});
	const lastCategoriesRef = useRef<string[]>(initialCategories);
	useEffect(() => {
		if (!detail) {
			lastCategoriesRef.current = [];
			setCategoriesState({ value: [], dirty: false });
			return;
		}
		const incoming = detail.categories ? [...detail.categories] : [];
		const prev = lastCategoriesRef.current;
		if (!arraysEqual(incoming, prev)) {
			lastCategoriesRef.current = incoming;
			setCategoriesState({ value: incoming, dirty: false });
		}
	}, [detail]);

	const normalizedPreview = useMemo(() => {
		if (!previewSrc) return null;
		if (/^https?:/i.test(previewSrc)) return previewSrc;
		if (previewSrc.startsWith("/api/receipts/")) return previewSrc;
		return previewSrc;
	}, [previewSrc]);
	const normalizedDownload = useMemo(() => {
		if (!downloadUrl) return null;
		if (/^https?:/i.test(downloadUrl)) return downloadUrl;
		if (downloadUrl.startsWith("/api/receipts/")) return downloadUrl;
		return downloadUrl;
	}, [downloadUrl]);
	const persistCategories = useCallback(
		async (next: string[]) => {
			setCategoriesState({ value: next, dirty: true });
			try {
				await updateCategories(next);
				lastCategoriesRef.current = next;
				setCategoriesState({ value: next, dirty: false });
			} catch (error) {
				console.error("Failed to save categories", error);
				const fallback = detail?.categories ? [...detail.categories] : [];
				lastCategoriesRef.current = fallback;
				setCategoriesState({ value: fallback, dirty: false });
			}
		},
		[updateCategories, detail]
	);
	const categories = categoriesState.value;

	async function handleReprocess() {
		if (!receipt) return;
		try {
			let token: string | null = null;
			try {
				token = await getToken?.();
			} catch {
				/* ignore */
			}
			await fetch(`/api/receipts/${encodeURIComponent(String(receipt.id))}/reprocess`, {
				method: "POST",
				headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) },
			});
		} catch {
			/* ignore */
		}
	}
	async function handleDelete() {
		if (!receipt) return;
		try {
			let token: string | null = null;
			try {
				token = await getToken?.();
			} catch {
				/* ignore */
			}
			await fetch(`/api/receipts/${encodeURIComponent(String(receipt.id))}`, {
				method: "DELETE",
				headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) },
			});
			router.push("/dashboard/receipts");
		} catch {
			/* ignore */
		}
	}

	if (loading || !detail) return <Box sx={{ p: 4, color: "#EDEDED" }}>Loading receipt…</Box>;

	return (
		<Box sx={{ bgcolor: "#0B0B0D", color: "#EDEDED", minHeight: "100vh", display: "flex", flexDirection: "column" }}>
			<TopBar
				brandName={BRAND_NAME}
				status={capitalize(detail.status)}
				accuracy={detail.predictionAccuracy}
				onReprocess={handleReprocess}
				onDelete={handleDelete}
				downloadHref={normalizedDownload}
			/>
			<Box
				sx={{
					flex: "1 1 auto",
					p: 2,
					display: "grid",
					gridTemplateColumns: { xs: "1fr", md: "260px 1fr 340px" },
					gridTemplateRows: "auto 1fr auto",
					gap: 2,
					alignItems: "start",
				}}
			>
				<Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
					<ActionNav
						onReprocess={handleReprocess}
						onDelete={handleDelete}
						downloadHref={normalizedDownload}
						onUpload={() => {}}
					/>
					<LeftCategories
						assigned={categories}
						onChange={persistCategories}
						saving={updatingCategories}
						error={categoriesError}
					/>
				</Box>
				<Box sx={{ display: "flex", flexDirection: "column", gap: 2, minHeight: 0 }}>
					<ImageToolbar onPlay={handleReprocess} onStep={() => {}} />
					<ReceiptViewer
						imageUrl={detail.imageUrl}
						fallbackUrl={normalizedDownload || normalizedPreview || undefined}
						bboxes={detail.bboxes}
						activeBboxId={null}
					/>
				</Box>
				<Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
					<ExtractedSummaryCard
						store={detail.fields.find((f) => f.key === "vendor")?.value || "—"}
						date={detail.fields.find((f) => f.key === "date")?.value || "—"}
						total={detail.fields.find((f) => f.key === "amount")?.value || "—"}
					/>
					<LabeledCategoriesCard categories={categories} />
				</Box>
				<Box sx={{ gridColumn: { xs: "1 / -1", md: "2 / span 1" } }}>
					<DataExtractedTable
						store={detail.fields.find((f) => f.key === "vendor")?.value || "—"}
						date={detail.fields.find((f) => f.key === "date")?.value || "—"}
						total={detail.fields.find((f) => f.key === "amount")?.value || "—"}
					/>
				</Box>
			</Box>
		</Box>
	);
}
