import * as React from "react";

import { appConfig } from "@/config/app";
import { ResetPasswordForm } from "@/components/auth/custom/reset-password-form";
import { SplitLayout } from "@/components/auth/split-layout";

export const metadata = { title: `Reset password | Custom | Auth | ${appConfig.name}` };

export default function Page() {
	return (
		<SplitLayout>
			<ResetPasswordForm />
		</SplitLayout>
	);
}
