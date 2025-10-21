"use client";

import React from "react";
import { useAuth } from "@clerk/nextjs";

import { AppChat } from "@/components/dashboard/overview/app-chat";

type Msg = {
	id: string;
	content: string;
	author: { name: string; avatar: string; status: string };
	createdAt: Date;
};

export function AppChatClient({ limit = 5 }: { limit?: number }) {
	const { getToken, isSignedIn } = useAuth();
	const [messages, setMessages] = React.useState<Msg[] | null>(null);
	const [error, setError] = React.useState<string | null>(null);

	React.useEffect(() => {
		let active = true;
		const controller = new AbortController();
		(async () => {
			try {
				if (!isSignedIn) {
					setError("Sign in to view support chats.");
					setMessages([]);
					return;
				}
				const token = await getToken();
				const API_BASE =
					process.env.NEXT_PUBLIC_API_URL || process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
				const url = new URL(`${API_BASE}/support/threads`);
				url.searchParams.set("limit", String(limit));
				const res = await fetch(url.toString(), {
					headers: token ? { Authorization: `Bearer ${token}` } : undefined,
					signal: controller.signal,
					cache: "no-store",
				});
				if (!res.ok) {
					if (res.status === 401) setError("Unauthorized. Check backend Clerk config or sign in.");
					throw new Error(`support ${res.status}`);
				}
				const rows: Array<{
					id?: string | number;
					content?: string;
					last_message?: string;
					subject?: string;
					author?: { name?: string; avatar?: string; status?: string };
					user?: { name?: string; avatar?: string; status?: string };
					created_at?: string;
					ts?: string;
				}> = await res.json();
				const mapped: Msg[] = (Array.isArray(rows) ? rows : []).slice(0, limit).map((m, idx: number) => ({
					id: String(m.id ?? `MSG-${idx}`),
					content: String(m.content ?? m.last_message ?? m.subject ?? ""),
					author: {
						name: String(m.author?.name ?? m.user?.name ?? "User"),
						avatar: String(m.author?.avatar ?? m.user?.avatar ?? "/assets/avatar-1.png"),
						status: String(m.author?.status ?? m.user?.status ?? "offline"),
					},
					createdAt: new Date(m.created_at ?? m.ts ?? Date.now()),
				}));
				if (active) setMessages(mapped);
			} catch {
				if (active) setMessages([]);
			}
		})();
		return () => {
			active = false;
			controller.abort();
		};
	}, [getToken, isSignedIn, limit]);

	return (
		<div>
			{error ? <div style={{ fontSize: 12, color: "#888", marginBottom: 8 }}>{error}</div> : null}
			<AppChat messages={messages ?? []} />
		</div>
	);
}
