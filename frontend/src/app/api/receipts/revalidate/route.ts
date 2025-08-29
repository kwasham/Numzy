import { revalidateTag } from "next/cache";
import { auth } from "@clerk/nextjs/server";

export const dynamic = "force-dynamic";

interface RevalidateBody {
	receiptId?: string;
}

export async function POST(req: Request) {
	const { userId } = auth();
	const devBypass = process.env.DEV_AUTH_BYPASS === "true" || process.env.NEXT_PUBLIC_DEV_AUTH_BYPASS === "true";
	let body: RevalidateBody = {};
	try {
		body = (await req.json()) as RevalidateBody;
	} catch {
		/* ignore parse errors */
	}
	const { receiptId } = body;
	if (userId) {
		if (receiptId) revalidateTag(`receipt-${receiptId}`);
		revalidateTag(`receipt-summary-${userId}`);
		return new Response("ok", { headers: { "x-revalidate-mode": "auth" } });
	}
	// Silent no-op for unauthenticated users to avoid console 401 noise (e.g. dev bypass or public demo)
	if (devBypass) {
		return new Response("ok", { headers: { "x-revalidate-mode": "dev-bypass" } });
	}
	return new Response("ignored", { status: 200, headers: { "x-revalidate-mode": "anon" } });
}
