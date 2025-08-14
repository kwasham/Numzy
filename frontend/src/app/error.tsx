"use client";

import React from "react";
import * as Sentry from "@sentry/nextjs";

export default function RouteError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
	React.useEffect(() => {
		Sentry.captureException(error);
	}, [error]);

	return (
		<div style={{ padding: "2rem", fontFamily: "system-ui" }}>
			<h2 style={{ fontSize: "1.25rem", fontWeight: 600, marginBottom: "0.75rem" }}>
				Something went wrong in this route.
			</h2>
			<p style={{ color: "#555", marginBottom: "1rem" }}>{error.message}</p>
			<div style={{ display: "flex", gap: "0.5rem" }}>
				<button
					onClick={() => reset()}
					style={{
						background: "#2563eb",
						color: "#fff",
						padding: "0.5rem 0.75rem",
						borderRadius: 4,
						border: "none",
						cursor: "pointer",
					}}
				>
					Retry
				</button>
				<button
					onClick={() => {
						globalThis.location.href = "/";
					}}
					style={{
						background: "#374151",
						color: "#fff",
						padding: "0.5rem 0.75rem",
						borderRadius: 4,
						border: "none",
						cursor: "pointer",
					}}
				>
					Home
				</button>
			</div>
		</div>
	);
}
