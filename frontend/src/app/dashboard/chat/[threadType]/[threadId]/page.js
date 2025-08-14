import * as React from "react";

import { appConfig } from "@/config/app";
import { ThreadView } from "@/components/dashboard/chat/thread-view";

export const metadata = { title: `Thread | Chat | Dashboard | ${appConfig.name}` };

export default async function Page({ params }) {
	const { threadId, threadType } = await params;

	return <ThreadView threadId={threadId} threadType={threadType} />;
}
