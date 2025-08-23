"use client";

import React, { useEffect, useMemo } from "react";
import { Auth0Provider } from "@auth0/nextjs-auth0"; // use root export; client subpath not exported in this version

import { appConfig } from "@/config/app";
import { AuthStrategy } from "@/lib/auth-strategy";
import { AuthProvider as CognitoProvider } from "@/components/auth/cognito/auth-context";
import { AuthProvider as CustomAuthProvider } from "@/components/auth/custom/auth-context";
import { AuthProvider as SupabaseProvider } from "@/components/auth/supabase/auth-context";

// Lazy import Clerk only when needed to avoid adding it to the main bundle for other strategies
const ClerkBoundary: React.FC<{ children: React.ReactNode }> = ({ children }) => {
	const publishableKey = process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY;
	const [ClerkProvider, setClerkProvider] = React.useState<React.ComponentType<{ children: React.ReactNode }> | null>(
		null
	);

	useEffect(() => {
		let active = true;
		if (!publishableKey) {
			console.error("[auth] Missing NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY – Clerk cannot initialize.");
			return;
		}
		import("@clerk/nextjs")
			.then((mod) => {
				if (active) setClerkProvider(() => mod.ClerkProvider);
			})
			.catch((error) => {
				console.error("[auth] Failed dynamic import of @clerk/nextjs", error);
			});
		return () => {
			active = false;
		};
	}, [publishableKey]);

	if (!publishableKey) {
		return children; // let app render; protected routes will still fail gracefully
	}
	if (!ClerkProvider) {
		return null; // brief splash blank; could add skeleton
	}
	return <ClerkProvider publishableKey={publishableKey}>{children}</ClerkProvider>;
};

export const UnifiedAuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
	const strategy = appConfig.authStrategy;

	const wrapped = useMemo(() => {
		switch (strategy) {
			case AuthStrategy.AUTH0: {
				return <Auth0Provider>{children}</Auth0Provider>;
			}
			case AuthStrategy.CLERK: {
				return <ClerkBoundary>{children}</ClerkBoundary>;
			}
			case AuthStrategy.COGNITO: {
				return <CognitoProvider>{children}</CognitoProvider>;
			}
			case AuthStrategy.CUSTOM: {
				return <CustomAuthProvider>{children}</CustomAuthProvider>;
			}
			case AuthStrategy.SUPABASE: {
				return <SupabaseProvider>{children}</SupabaseProvider>;
			}
			default: {
				return <>{children}</>; // NONE
			}
		}
	}, [strategy, children]);

	return wrapped;
};
