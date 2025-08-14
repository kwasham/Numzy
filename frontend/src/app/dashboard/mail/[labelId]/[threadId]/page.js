import * as React from "react";

import { appConfig } from "@/config/app";
import { ThreadView } from "@/components/dashboard/mail/thread-view";

export const metadata = { title: `Thread | Mail | Dashboard | ${appConfig.name}` };

export default async function Page({ params }) {
	const { threadId } = await params;

	return <ThreadView threadId={threadId} />;
}
