import * as React from "react";

import { appConfig } from "@/config/app";
import { SplitLayout } from "@/components/auth/split-layout";
import { ResetPasswordForm } from "@/components/auth/supabase/reset-password-form";

export const metadata = { title: `Reset password | Supabase | Auth | ${appConfig.name}` };

export default function Page() {
	return (
		<SplitLayout>
			<ResetPasswordForm />
		</SplitLayout>
	);
}
