import * as React from "react";
import { redirect } from "next/navigation";

import { appConfig } from "@/config/app";
import { paths } from "@/paths";
import { logger } from "@/lib/default-logger";
import { createClient as createSupabaseClient } from "@/lib/supabase/server";
import { SplitLayout } from "@/components/auth/split-layout";
import { SignInForm } from "@/components/auth/supabase/sign-in-form";

export const metadata = { title: `Sign in | Supabase | Auth | ${appConfig.name}` };

export default async function Page() {
	const supabaseClient = await createSupabaseClient();
	const { data } = await supabaseClient.auth.getUser();

	if (data.user) {
		logger.debug("[Sign in] User is authenticated, redirecting to dashboard");
		redirect(paths.dashboard.overview);
	}

	return (
		<SplitLayout>
			<SignInForm />
		</SplitLayout>
	);
}
