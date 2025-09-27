import { NextResponse } from "next/server";

// Public endpoint: returns the Clerk publishable key so purely static exported
// marketing HTML can bootstrap Clerk JS at runtime without embedding env vars
// directly in a copied /public file.
export function GET() {
	const publishableKey = process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY || "";
	return NextResponse.json({ publishableKey });
}
