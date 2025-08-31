"use client";

import * as React from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@clerk/nextjs";

import { paths } from "@/paths";
import { previewCache, setPreview } from "@/components/dashboard/receipts/receipt-cache";
import { ReceiptModal } from "@/components/dashboard/receipts/receipt-modal";

interface ReceiptModalGateProps {
	// Optionally control how long we'll wait before giving up (ms)
	timeoutMs?: number;
}

export function ReceiptModalGate({ timeoutMs = 8000 }: ReceiptModalGateProps) {
	const search = useSearchParams();
	const router = useRouter();
	const previewId = search?.get("previewId") || null;
	const { getToken } = useAuth();
	const [ready, setReady] = React.useState(false);
	const [src, setSrc] = React.useState<string | null>(null);

	// When previewId changes begin prefetch (if needed) and only mark ready when loaded.
	React.useEffect(() => {
		let cancelled = false;
		setReady(false);
		setSrc(null);
		if (!previewId) return;
		(async () => {
			const existing = previewCache.get(previewId) || previewCache.get(String(previewId));
			if (existing?.loaded) {
				if (!cancelled) {
					setSrc(existing.src);
					setReady(true);
				}
				return;
			}
			// Auth handled server-side; avoid leaking JWT in query params.
			const thumb = `/api/receipts/${encodeURIComponent(previewId)}/thumb`;
			try {
				const controller = new AbortController();
				const tId = setTimeout(() => {
					controller.abort();
				}, timeoutMs);
				const res = await fetch(thumb, { cache: "no-store", signal: controller.signal });
				clearTimeout(tId);
				if (!res.ok) throw new Error("thumb fetch failed");
				const ct = res.headers.get("content-type") || "";
				if (!ct.startsWith("image")) throw new Error("not image");
				const blob = await res.blob();
				if (cancelled) return;
				const objectUrl = URL.createObjectURL(blob);
				setPreview(previewId, objectUrl, true, true);
				setSrc(objectUrl);
				setReady(true);
			} catch {
				if (cancelled) return;
				// On failure we abort opening entirely; remove previewId param.
				router.replace(paths.dashboard.receipts);
			}
		})();
		return () => {
			cancelled = true;
		};
	}, [previewId, getToken, router, timeoutMs]);

	if (!previewId || !ready) return null; // gate: nothing rendered until image ready
	return <ReceiptModal open={Boolean(previewId && ready)} receiptId={previewId} previewSrc={src || undefined} />;
}

export default ReceiptModalGate;
