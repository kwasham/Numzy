"use client";

import * as React from "react";
import { SignIn } from "@clerk/nextjs";

interface ClerkSignInCardProps {
	redirectTo?: string;
}

export function ClerkSignInCard({ redirectTo = "/dashboard" }: ClerkSignInCardProps) {
	const [mounted, setMounted] = React.useState(false);
	React.useEffect(() => setMounted(true), []);

	if (!mounted) {
		return (
			<div style={{ textAlign: "center", padding: "40px 0", color: "var(--neutral-200,#999)", fontSize: 14 }}>
				Loading secure sign‑in…
			</div>
		);
	}

	// Appearance tweaks to better blend into Webflow card visuals
	const appearance = {
		variables: {
			colorPrimary: "#6366f1",
			colorText: "#e5e7eb",
			colorBackground: "transparent",
			fontSize: "14px",
			borderRadius: "8px",
		},
		elements: {
			card: {
				background: "transparent",
				boxShadow: "none",
				border: "1px solid rgba(255,255,255,0.08)",
				backdropFilter: "blur(6px)",
			},
			headerTitle: { fontSize: "28px", fontWeight: 600 },
			headerSubtitle: { fontSize: "14px", opacity: 0.8 },
			socialButtonsBlockButton: { borderRadius: 8 },
			formButtonPrimary: { borderRadius: 8 },
		},
		// eslint-disable-next-line @typescript-eslint/no-explicit-any -- Clerk appearance typing is optional here
	} as any;

	return (
		<SignIn
			routing="path"
			path="/sign-in"
			signUpUrl="/sign-up"
			afterSignInUrl={redirectTo}
			redirectUrl={redirectTo}
			appearance={appearance}
		/>
	);
}
