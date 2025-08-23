import * as React from "react";
import { Auth0Provider } from "@auth0/nextjs-auth0";
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

// Dynamic auth provider selection (original strategy-based logic)
// For Clerk we use a dynamic import to avoid adding it to the bundle when unused.

export default async function Layout({ children }) {
	const settings = await getPersistedSettings();
	const direction = settings.direction ?? appConfig.direction;
	const language = settings.language ?? appConfig.language;

	let AuthProvider = React.Fragment;
	let clerkPublishableKey = process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY;

	switch (appConfig.authStrategy) {
		case AuthStrategy.AUTH0: {
			AuthProvider = Auth0Provider;
			break;
		}
		case AuthStrategy.CLERK: {
			const { ClerkProvider } = await import("@clerk/nextjs");
			const ClerkWrapper = (props) => <ClerkProvider publishableKey={clerkPublishableKey} {...props} />;
			ClerkWrapper.displayName = "ClerkWrapper";
			AuthProvider = ClerkWrapper;
			break;
		}
		case AuthStrategy.COGNITO: {
			AuthProvider = CognitoProvider;
			break;
		}
		case AuthStrategy.CUSTOM: {
			AuthProvider = CustomAuthProvider;
			break;
		}
		case AuthStrategy.SUPABASE: {
			AuthProvider = SupabaseProvider;
			break;
		}
		default: {
			AuthProvider = React.Fragment;
		}
	}

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
