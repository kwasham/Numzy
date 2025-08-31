import { auth } from "@clerk/nextjs/server";

// Simple in-memory suppression of repeated auth failures to avoid noisy 403 logs.
// receiptId -> retry timestamp (ms)
const authFailureBackoff: Map<string, number> = new Map();
const AUTH_FAIL_COOLDOWN_MS = 30_000; // 30s

export const dynamic = "force-dynamic";

export async function GET(req: Request, ctx: { params: { id: string } | Promise<{ id: string }> }) {
	const { userId, getToken } = auth();
	const devBypass = process.env.DEV_AUTH_BYPASS === "true" || process.env.NEXT_PUBLIC_DEV_AUTH_BYPASS === "true";
	const rawParams = await ctx.params;
	const receiptId = rawParams.id;
	const backend = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
	// We intentionally do NOT trust or use a client-provided token query param here:
	// leaking the Clerk JWT into the URL was causing 401s once the token expired & also pollutes logs / caches.
	// Instead we obtain the server-side token (if authenticated) and forward as Authorization only to the
	// signing endpoint; the returned signed URL lets us fetch the thumbnail bytes without auth headers.
	const headerToken = userId ? await getToken?.() : null;
	// Rate-limit attempts if we recently failed auth
	const now = Date.now();
	const retryAt = authFailureBackoff.get(receiptId);
	if (retryAt && retryAt > now) {
		return new Response(null, { status: 204, headers: { "x-thumb-suppressed": "1" } });
	}
	// First ask for a signed thumbnail URL (auth required to prove ownership)
	const signRes = await fetch(`${backend}/receipts/${encodeURIComponent(receiptId)}/thumbnail_url`, {
		headers: headerToken ? { Authorization: `Bearer ${headerToken}` } : undefined,
		cache: "no-store", // we only cache the image bytes
	});
	if (!signRes.ok) {
		// Convert auth issues (401/403) into silent 204 to reduce log noise and set backoff.
		if (signRes.status === 401 || signRes.status === 403) {
			authFailureBackoff.set(receiptId, now + AUTH_FAIL_COOLDOWN_MS);
			return new Response(null, { status: 204, headers: { "x-thumb-auth": "fail" } });
		}
		return new Response(null, { status: signRes.status });
	}
	const { url } = await signRes.json().catch(() => ({ url: null }));
	if (!url) return new Response(null, { status: 204 });
	const abs = `${backend}${url}`;
	const img = await fetch(abs, {
		cache: "force-cache",
		next: { revalidate: 30, tags: ["receipt-thumb", `receipt-${receiptId}`] },
	});
	return new Response(await img.arrayBuffer(), {
		status: img.status,
		headers: {
			"content-type": img.headers.get("content-type") || "image/jpeg",
			"x-receipt-thumb-mode": userId ? "auth" : devBypass ? "dev-bypass" : "anon",
		},
	});
}
