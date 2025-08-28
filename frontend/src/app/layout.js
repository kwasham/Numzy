import * as React from "react";
import { Auth0Provider } from "@auth0/nextjs-auth0";
import { ClerkProvider } from "@clerk/nextjs";
import InitColorSchemeScript from "@mui/material/InitColorSchemeScript";

import "@/styles/global.css";

import { appConfig } from "@/config/app";
import { AuthStrategy } from "@/lib/auth-strategy";
import { getSettings as getPersistedSettings } from "@/lib/settings";
import { AuthProvider as CognitoProvider } from "@/components/auth/cognito/auth-context";
import { AuthProvider as CustomAuthProvider } from "@/components/auth/custom/auth-context";
import { AuthProvider as SupabaseProvider } from "@/components/auth/supabase/auth-context";
import { Analytics } from "@/components/core/analytics";
import { EmotionCacheProvider } from "@/components/core/emotion-cache";
import { I18nProvider } from "@/components/core/i18n-provider";
import { LocalizationProvider } from "@/components/core/localization-provider";
import { Rtl } from "@/components/core/rtl";
import { SettingsButton } from "@/components/core/settings/settings-button";
import { SettingsProvider } from "@/components/core/settings/settings-context";
import { ThemeProvider } from "@/components/core/theme-provider";
import { Toaster } from "@/components/core/toaster";

export const metadata = { title: appConfig.name };

export const viewport = {
	width: "device-width",
	initialScale: 1,
	themeColor: appConfig.themeColor,
};

// Define the AuthProvider based on the selected auth strategy
// Remove this block if you are not using any auth strategy

let AuthProvider = React.Fragment;

if (appConfig.authStrategy === AuthStrategy.AUTH0) {
	AuthProvider = Auth0Provider;
}

// For Clerk we must pass the publishableKey; using the raw ClerkProvider without
// the key causes runtime "Failed to load Clerk" errors (especially after sign out)
// because the script cannot auto-discover configuration in this setup.
if (appConfig.authStrategy === AuthStrategy.CLERK) {
	const publishableKey = process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY;
	AuthProvider = function ClerkAuthBoundary({ children }) {
		if (!publishableKey) {
			if (process.env.NODE_ENV !== "production") {
				console.error("[auth] Missing NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY – rendering children without ClerkProvider");
			}
			return <>{children}</>; // Fail open so the rest of the app still renders
		}
		return <ClerkProvider publishableKey={publishableKey}>{children}</ClerkProvider>;
	};
}

if (appConfig.authStrategy === AuthStrategy.COGNITO) {
	AuthProvider = CognitoProvider;
}

if (appConfig.authStrategy === AuthStrategy.CUSTOM) {
	AuthProvider = CustomAuthProvider;
}

if (appConfig.authStrategy === AuthStrategy.SUPABASE) {
	AuthProvider = SupabaseProvider;
}

export default async function Layout({ children }) {
	const settings = await getPersistedSettings();
	const direction = settings.direction ?? appConfig.direction;
	const language = settings.language ?? appConfig.language;

	return (
		<html dir={direction} lang={language} suppressHydrationWarning>
			<body>
				<InitColorSchemeScript attribute="class" />
				<AuthProvider>
					<Analytics>
						<LocalizationProvider>
							<SettingsProvider settings={settings}>
								<I18nProvider lng={language}>
									<EmotionCacheProvider options={{ key: "mui" }}>
										<Rtl direction={direction}>
											<ThemeProvider>
												{children}
												<SettingsButton />
												<Toaster position="bottom-right" />
											</ThemeProvider>
										</Rtl>
									</EmotionCacheProvider>
								</I18nProvider>
							</SettingsProvider>
						</LocalizationProvider>
					</Analytics>
				</AuthProvider>
			</body>
		</html>
	);
}
