// Root application page: redirect to main dashboard.
// Keeping this minimal server component to avoid layout duplication.
import { redirect } from "next/navigation";

export default function RootPage() {
	redirect("/dashboard");
	return null; // (unreachable, but satisfies return type expectations)
}
