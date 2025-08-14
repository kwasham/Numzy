import * as React from "react";

import { appConfig } from "@/config/app";
import { ComposeView } from "@/components/dashboard/chat/compose-view";

export const metadata = { title: `Compose | Chat | Dashboard | ${appConfig.name}` };

export default function Page() {
	return <ComposeView />;
}
