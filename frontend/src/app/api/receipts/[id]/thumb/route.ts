import { auth } from "@clerk/nextjs/server";

export const dynamic = "force-dynamic";

export async function GET(req: Request, ctx: { params: { id: string } | Promise<{ id: string }> }) {
	const { userId, getToken } = auth();
	const devBypass = process.env.DEV_AUTH_BYPASS === "true" || process.env.NEXT_PUBLIC_DEV_AUTH_BYPASS === "true";
	const rawParams = await ctx.params;
	const receiptId = rawParams.id;
	const backend = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
	const urlObj = new URL(req.url);
	const tokenFromQuery = urlObj.searchParams.get("token");
	const headerToken = userId ? await getToken?.() : null;
	const token = headerToken || tokenFromQuery;
	// First ask for a signed thumbnail URL
	const signRes = await fetch(`${backend}/receipts/${encodeURIComponent(receiptId)}/thumbnail_url`, {
		headers: token ? { Authorization: `Bearer ${token}` } : undefined,
		cache: "no-store", // we only cache the image bytes
	});
	if (!signRes.ok) return new Response(null, { status: signRes.status });
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
