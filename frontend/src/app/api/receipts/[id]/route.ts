import { auth } from "@clerk/nextjs/server";

export const dynamic = "force-dynamic";

export async function GET(req: Request, ctx: { params: { id: string } | Promise<{ id: string }> }) {
	const { userId, getToken } = auth();
	const devBypass = process.env.DEV_AUTH_BYPASS === "true" || process.env.NEXT_PUBLIC_DEV_AUTH_BYPASS === "true";
	// Support Next.js experimental async params (must await) while remaining compatible with sync object.
	const rawParams = await ctx.params; // if already plain object, await is a no-op
	const receiptId = rawParams.id;
	const backend = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
	const urlObj = new URL(req.url);
	const tokenFromQuery = urlObj.searchParams.get("token");
	const headerToken = userId ? await getToken?.() : null;
	const token = headerToken || tokenFromQuery;
	const res = await fetch(`${backend}/receipts/${encodeURIComponent(receiptId)}`, {
		headers: token ? { Authorization: `Bearer ${token}` } : undefined,
		cache: "force-cache",
		next: userId ? { revalidate: 5, tags: [`receipt-${receiptId}`, `receipt-summary-${userId}`] } : { revalidate: 5 },
	});
	if (!res.ok) return new Response("not found", { status: res.status });
	const data = await res.json();
	return new Response(JSON.stringify(data), {
		status: 200,
		headers: {
			"content-type": "application/json",
			"x-receipt-mode": userId ? "auth" : devBypass ? "dev-bypass" : "anon",
		},
	});
}
