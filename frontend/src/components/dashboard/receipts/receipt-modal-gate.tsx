"use client";

import { useSearchParams } from "next/navigation";

import { ReceiptModal } from "@/components/dashboard/receipts/receipt-modal";

// Simplified gate: render the modal immediately when a previewId is present.
// Image fetching & retries are fully handled inside useReceiptDetails now.
export function ReceiptModalGate() {
	const search = useSearchParams();
	const previewId = search?.get("previewId") || null;
	if (!previewId) return null;
	return <ReceiptModal open receiptId={previewId} />;
}

export default ReceiptModalGate;
