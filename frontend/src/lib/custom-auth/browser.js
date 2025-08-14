import { paths } from "@/paths";

export async function getUser() {
	const res = await fetch(paths.auth.custom.profile);
	const data = await res.json();

	return { data: { user: data.user } };
}
