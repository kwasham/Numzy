// Root route: redirect users to the dashboard (adjust target if you add a marketing homepage)
import { redirect } from "next/navigation";

export const metadata = { title: "Numzy" };

export default function RootRedirect() {
	redirect("/dashboard");
}
