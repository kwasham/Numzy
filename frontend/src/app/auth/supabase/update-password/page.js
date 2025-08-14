import * as React from "react";

import { appConfig } from "@/config/app";
import { SplitLayout } from "@/components/auth/split-layout";
import { UpdatePasswordForm } from "@/components/auth/supabase/update-password-form";

export const metadata = { title: `Update password | Supabase | Auth | ${appConfig.name}` };

export default function Page() {
	return (
		<SplitLayout>
			<UpdatePasswordForm />
		</SplitLayout>
	);
}
