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
	let signRes: Response;
	try {
		signRes = await fetch(`${backend}/receipts/${encodeURIComponent(receiptId)}/thumbnail_url`, {
			headers: headerToken ? { Authorization: `Bearer ${headerToken}` } : undefined,
			cache: "no-store", // we only cache the image bytes
		});
	} catch {
		// Network or fetch error to backend signing endpoint
		return placeholderResponse("sign-error", undefined, "proxy-sign-error");
	}
	if (!signRes.ok) {
		if (signRes.status === 401 || signRes.status === 403) {
			// Auth failure: backoff + placeholder instead of 204 so UI can still show an image box.
			authFailureBackoff.set(receiptId, now + AUTH_FAIL_COOLDOWN_MS);
			return placeholderResponse("auth-fail", undefined, "proxy-auth-fail");
		}
		// Any other upstream error: return placeholder rather than bubbling a 5xx to the browser image tag
		return placeholderResponse("sign-upstream", signRes.status, "proxy-sign-upstream");
	}
	const { url } = await signRes.json().catch(() => ({ url: null }));
	if (!url) {
		// No signed URL returned (unexpected) – provide placeholder.
		return placeholderResponse("no-url", undefined, "proxy-no-url");
	}
	const abs = `${backend}${url}`;
	let img: Response;
	try {
		img = await fetch(abs, { cache: "no-store" });
		const upstreamStage = img.headers.get("x-thumb-stage") || undefined;
		const upstreamFallback = img.headers.get("x-thumb-fallback");
		if (!img.ok || !(img.headers.get("content-type") || "").startsWith("image")) {
			return placeholderResponse("bad-upstream", img.status, upstreamStage || "proxy-bad-upstream");
		}
		// If upstream explicitly sets x-thumb-fallback=0 treat it as a real image even if stage suggests placeholder
		return new Response(await img.arrayBuffer(), {
			status: 200,
			headers: {
				"content-type": img.headers.get("content-type") || "image/jpeg",
				"x-receipt-thumb-mode": userId ? "auth" : devBypass ? "dev-bypass" : "anon",
				...(upstreamStage ? { "x-thumb-stage": upstreamStage } : {}),
				...(upstreamFallback ? { "x-thumb-fallback": upstreamFallback } : {}),
			},
		});
	} catch {
		return placeholderResponse("fetch-error", undefined, "proxy-fetch-error");
	}
}

// Small transparent PNG (1x1) with headers to indicate placeholder reason and stage.
function placeholderResponse(reason: string, upstreamStatus?: number, stage?: string) {
	const tinyBase64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMB/af8w8sAAAAASUVORK5CYII=";
	const body = Buffer.from(tinyBase64, "base64");
	return new Response(body, {
		status: 200,
		headers: {
			"content-type": "image/png",
			"x-thumb-fallback": reason,
			...(stage ? { "x-thumb-stage": stage } : {}),
			...(upstreamStatus ? { "x-upstream-status": String(upstreamStatus) } : {}),
		},
	});
}
