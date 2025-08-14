import { NextResponse } from "next/server";

import { getUser } from "@/lib/custom-auth/server";

export async function GET() {
	const { data, error } = await getUser();

	if (error) {
		return new NextResponse(error, { status: 500 });
	}

	if (!data) {
		return new NextResponse("Unauthorized", { status: 401 });
	}

	return NextResponse.json({ user: data.user });
}
