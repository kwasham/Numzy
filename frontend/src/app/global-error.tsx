"use client";

import React from "react";
import * as Sentry from "@sentry/nextjs";

export default function GlobalError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
	React.useEffect(() => {
		Sentry.captureException(error);
	}, [error]);

	return (
		<html>
			<body style={{ fontFamily: "system-ui", padding: "3rem", maxWidth: 640, margin: "0 auto" }}>
				<h1 style={{ fontSize: "1.5rem", marginBottom: "1rem" }}>Something went wrong</h1>
				<p style={{ color: "#555", marginBottom: "1.25rem" }}>
					An unexpected error occurred. Our team has been notified.
				</p>
				<code
					style={{
						display: "block",
						background: "#f5f5f5",
						padding: "0.75rem",
						borderRadius: 4,
						fontSize: "0.8rem",
						marginBottom: "1.25rem",
						overflowX: "auto",
					}}
				>
					{error?.message || "Unknown error"}
				</code>
				<button
					onClick={() => reset()}
					style={{
						background: "#111827",
						color: "#fff",
						padding: "0.625rem 1rem",
						borderRadius: 6,
						border: "none",
						cursor: "pointer",
					}}
				>
					Try again
				</button>
			</body>
		</html>
	);
}
