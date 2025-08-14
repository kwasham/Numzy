import { NextResponse } from "next/server";

import { getAppUrl } from "@/lib/get-app-url";
import { createClient } from "@/lib/supabase/server";

// NOTE: The sign out process can be done in the client side as well.
//  The server side approach is used to have a consistent behavior across different auth strategies.
//  We encourage you to use the client side approach because it is faster,
//  more efficient and prevents the server from being a bottleneck.

export async function GET() {
	const supabaseClient = await createClient();
	await supabaseClient.auth.signOut();
	const res = new NextResponse(undefined, { status: 307 });
	res.headers.set("Location", getAppUrl().toString());

	return res;
}
