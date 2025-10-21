"use client";

import { FormEvent, useState } from "react";
import { useSignIn } from "@clerk/nextjs";
import { Box, Button, Link, Typography } from "@mui/material";
import { alpha, useTheme } from "@mui/material/styles";

import { SignInThemeProvider } from "./sign-in-theme";

const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
	event.preventDefault();
};

function SignInContent() {
	const theme = useTheme();
	const { palette, shadows, typography } = theme;
	const neutrals = palette.neutral;
	const { signIn, isLoaded } = useSignIn();

	const [email, setEmail] = useState("");
	const [password, setPassword] = useState("");
	const [rememberMe, setRememberMe] = useState(false);

	const cardBackground = alpha(palette.primary.main, 0.41);
	const cardBorder = alpha(neutrals.colors100, 0.16);
	const inputBorder = alpha(neutrals.colors500, 0.7);
	const placeholderColor = neutrals.colors300;
	const dividerColor = alpha(neutrals.colors300, 0.6);
	const verticalHighlight = `linear-gradient(to bottom, ${alpha(neutrals.colors100, 0)}, ${alpha(neutrals.colors100, 0.82)}, ${alpha(neutrals.colors100, 0)})`;

	const handleGoogleClick = async () => {
		// Only attempt Clerk OAuth if the hook is ready (ClerkProvider present and loaded)
		if (!isLoaded || !signIn) {
			console.warn(
				"Clerk SignIn not loaded; ensure ClerkProvider is configured and NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY is set."
			);
			return;
		}
		try {
			await signIn.authenticateWithRedirect({
				strategy: "oauth_google",
				// Adjust redirect destinations as desired
				redirectUrl: "/",
				redirectUrlComplete: "/dashboard",
			});
		} catch (error) {
			console.error("Google OAuth redirect failed", error);
		}
	};

	return (
		<Box
			sx={{
				backgroundColor: palette.primary.main,
				color: neutrals.colors100,
				display: "flex",
				flexDirection: "column",
				minHeight: "100vh",
				overflow: "hidden",
				"use client";

				import { Box, Link, Typography } from "@mui/material";
					<Box sx={{ alignItems: "center", display: "flex", justifyContent: "center" }}>
						<Box component="a" href="/" sx={{ alignItems: "center", display: "inline-flex" }}>
				import { ClerkSignInCard } from "@/components/auth/clerk/clerk-sign-in-card";
							<Box
							/>
						</Box>
					</Box>
					const { palette, typography } = theme;
			</Box>
					display: "flex",
					flex: 1,
					justifyContent: "center",
					const dividerColor = alpha(neutrals.colors300, 0.6);
					pb: { xs: "160px", md: "200px" },
				}}
			>
				<Box sx={{ maxWidth: 940, mx: "auto", px: { xs: 2, sm: 3 }, width: "100%" }}>
							sx={{
								bottom: { xs: -120, md: -102 },
								left: { xs: -110, md: -80 },
								maxWidth: { xs: 260, md: 410 },
								opacity: 1,
								pointerEvents: "none",
								position: "absolute",
								width: "100%",
								zIndex: 1,
							}}
						/>

						<Box
							sx={{
								backdropFilter: "blur(48px)",
								backgroundColor: cardBackground,
								border: `1px solid ${cardBorder}`,
								borderRadius: "24px",
								boxShadow: `0 8px 32px ${palette.other.overlay40}`,
								mx: "auto",
								p: { xs: "40px 32px", sm: "48px 40px", md: "64px 98px" },
								position: "relative",
								width: "100%",
								zIndex: 2,
							}}
						>
							<Box
								sx={{
									background: verticalHighlight,
									bottom: "24px",
									left: "-1px",
									position: "absolute",
									top: "24px",
									width: "1px",
									zIndex: 0,
								}}
							/>
							<Box
								sx={{
									background: verticalHighlight,
									bottom: "24px",
									right: "-1px",
									position: "absolute",
									top: "24px",
									width: "1px",
									zIndex: 0,
								}}
							/>

							<Box sx={{ position: "relative", zIndex: 1 }}>
								<Box sx={{ mb: "32px", textAlign: "center" }}>
									<Typography
										component="h1"
										variant="h2"
										sx={{
											color: neutrals.colors100,
											fontSize: typography.h2.fontSize,
											fontWeight: typography.h2.fontWeight,
											letterSpacing: typography.h2.letterSpacing,
											lineHeight: typography.h2.lineHeight,
											mb: "16px",
										}}
									>
										Welcome back
									</Typography>
									<Typography
										variant="body1"
										sx={{
											color: neutrals.colors200,
											fontSize: typography.body1.fontSize,
											fontWeight: typography.body1.fontWeight,
											lineHeight: typography.body1.lineHeight,
											margin: 0,
										}}
									>
										Sign in with your organization credentials to continue.
									</Typography>
								</Box>

								<Box sx={{ display: "flex", justifyContent: "center" }}>
									<Box sx={{ width: "100%", maxWidth: 420 }}>
										<ClerkSignInCard redirectTo="/dashboard" />
									</Box>
								</Box>

								<Box sx={{ display: "flex", justifyContent: "center", textAlign: "center", mt: "32px" }}>
									<Typography variant="body1" sx={{ color: neutrals.colors200 }}>
										Need an account?{" "}
										<Link
											href="/sign-up"
											sx={{
												color: neutrals.colors100,
												textDecoration: "underline",
												"&:hover": { color: neutrals.colors200 },
											}}
										>
											Create one now
										</Link>
									</Typography>
								</Box>
							</Box>
						</Box>
					</Box>
				</Box>
			</Box>

			<Box component="footer" sx={{ backgroundColor: palette.primary.main, py: 5 }}>
				<Box sx={{ maxWidth: 940, mx: "auto", px: { xs: 2, sm: 3 } }}>
					<Box
						sx={{
							alignItems: "center",
							display: "flex",
							flexWrap: "wrap",
							gap: 3,
							justifyContent: "space-between",
							borderTop: `1px solid ${dividerColor}`,
							pt: 5,
						}}
					>
						<Box component="a" href="/" sx={{ alignItems: "center", display: "inline-flex" }}>
							<Box
								component="img"
								src="/images/logo-gpt-webflow-ecommerce-template.png"
								alt="GPT X Webflow Template - Logo"
								sx={{ height: "auto", maxWidth: 120 }}
							/>
						</Box>
						<Typography variant="body1" sx={{ color: neutrals.colors200, m: 0 }}>
							Copyright © GPT X | Designed by{" "}
							<Link
								href="https://brixtemplates.com/"
								target="_blank"
								rel="noreferrer"
								sx={{
									color: neutrals.colors100,
									textDecoration: "underline",
									"&:hover": { color: neutrals.colors200 },
								}}
							>
								BRIX Templates
							</Link>{" "}
							- Powered by{" "}
							<Link
								href="https://webflow.com/"
								target="_blank"
								rel="noreferrer"
								sx={{
									color: neutrals.colors100,
									textDecoration: "underline",
									"&:hover": { color: neutrals.colors200 },
								}}
							>
								Webflow
							</Link>
						</Typography>
					</Box>
				</Box>
			</Box>
		</Box>
	);
}

export default function SignIn() {
	return (
		<SignInThemeProvider>
			<SignInContent />
		</SignInThemeProvider>
	);
}
