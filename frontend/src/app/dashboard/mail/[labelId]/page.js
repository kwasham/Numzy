import * as React from "react";

import { appConfig } from "@/config/app";
import { ThreadsView } from "@/components/dashboard/mail/threads-view";

export const metadata = { title: `Mail | Dashboard | ${appConfig.name}` };

export default function Page() {
	return <ThreadsView />;
}
