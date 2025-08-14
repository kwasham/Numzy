import { NextResponse } from "next/server";

import { getAppUrl } from "@/lib/get-app-url";

export async function GET() {
	const res = new NextResponse(undefined, { status: 307 });

	// Cleanup tokens
	res.cookies.delete("sub");
	res.cookies.delete("access_token");
	res.cookies.delete("id_token");
	res.cookies.delete("refresh_token");

	const logoutUri = getAppUrl().toString();
	const redirectTo = new URL("/logout", process.env.NEXT_PUBLIC_COGNITO_DOMAIN);
	redirectTo.searchParams.append("client_id", process.env.NEXT_PUBLIC_COGNITO_CLIENT_ID);
	redirectTo.searchParams.append("logout_uri", logoutUri);
	res.headers.set("Location", redirectTo.toString());
	return res;
}
