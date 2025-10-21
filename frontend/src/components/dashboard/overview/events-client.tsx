"use client";

import React from "react";
import { useAuth } from "@clerk/nextjs";

import { Events } from "@/components/dashboard/overview/events";

type EventRow = { id: string; title: string; description?: string; createdAt: Date };

export function EventsClient({ limit = 4 }: { limit?: number }) {
	const { getToken, isSignedIn } = useAuth();
	const [events, setEvents] = React.useState<EventRow[] | null>(null);
	const [error, setError] = React.useState<string | null>(null);

	React.useEffect(() => {
		let active = true;
		const controller = new AbortController();
		(async () => {
			try {
				if (!isSignedIn) {
					setError("Sign in to view recent events.");
					setEvents([]);
					return;
				}
				const token = await getToken();
				const API_BASE =
					process.env.NEXT_PUBLIC_API_URL || process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
				const url = new URL(`${API_BASE}/events`);
				url.searchParams.set("limit", String(limit));
				const res = await fetch(url.toString(), {
					headers: token ? { Authorization: `Bearer ${token}` } : undefined,
					signal: controller.signal,
					cache: "no-store",
				});
				if (!res.ok) {
					if (res.status === 401) setError("Unauthorized. Check backend Clerk config or sign in.");
					throw new Error(`events ${res.status}`);
				}
				const rows: Array<{
					id?: string | number;
					title?: string;
					type?: string;
					description?: string;
					message?: string;
					ts?: string;
					created_at?: string;
				}> = await res.json();
				const mapped: EventRow[] = (Array.isArray(rows) ? rows : []).slice(0, limit).map((e, idx: number) => ({
					id: String(e.id ?? `EV-${idx}`),
					title: String(e.title ?? e.type ?? "Event"),
					description: String(e.description ?? e.message ?? ""),
					createdAt: new Date(e.ts ?? e.created_at ?? Date.now()),
				}));
				if (active) setEvents(mapped);
			} catch {
				if (active) setEvents([]);
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
			<Events events={events ?? []} />
		</div>
	);
}
