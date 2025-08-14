import * as React from "react";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

import { appConfig } from "@/config/app";
import { EmailNotifications } from "@/components/dashboard/settings/email-notifications";
import { PhoneNotifications } from "@/components/dashboard/settings/phone-notifications";

export const metadata = { title: `Notifications | Settings | Dashboard | ${appConfig.name}` };

export default function Page() {
	return (
		<Stack spacing={4}>
			<div>
				<Typography variant="h4">Notifications</Typography>
			</div>
			<Stack spacing={4}>
				<EmailNotifications />
				<PhoneNotifications />
			</Stack>
		</Stack>
	);
}
