import "server-only";

import { cookies } from "next/headers";

import { user } from "./data";

export async function getUser() {
	const cookieStore = await cookies();
	const token = cookieStore.get("access_token");

	if (!token) {
		return { data: { user: null } };
	}

	return { data: { user } };
}
