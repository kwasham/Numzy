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
				position: "relative",
			}}
		>
			<Box component="header" sx={{ backgroundColor: palette.primary.main, py: 4 }}>
				<Box sx={{ maxWidth: 940, mx: "auto", px: { xs: 2, sm: 3 } }}>
					<Box sx={{ alignItems: "center", display: "flex", justifyContent: "center" }}>
						<Box component="a" href="/" sx={{ alignItems: "center", display: "inline-flex" }}>
							<Box
								component="img"
								src="/images/logo-gpt-webflow-ecommerce-template.png"
								alt="GPT X Webflow Template - Logo"
								sx={{ height: "auto", maxWidth: 150 }}
							/>
						</Box>
					</Box>
				</Box>
			</Box>

			<Box
				component="section"
				sx={{
					alignItems: "center",
					display: "flex",
					flex: 1,
					justifyContent: "center",
					minHeight: "calc(100vh - 120px)",
					position: "relative",
					py: { xs: "80px", md: "80px" },
					pb: { xs: "160px", md: "200px" },
				}}
			>
				<Box sx={{ maxWidth: 940, mx: "auto", px: { xs: 2, sm: 3 }, width: "100%" }}>
					<Box sx={{ maxWidth: 660, mx: "auto", position: "relative" }}>
						<Box
							component="img"
							src="/images/shape-v11-gpt-x-webflow-template.png"
							alt=""
							sx={{
								maxWidth: { xs: 260, md: 460 },
								opacity: 1,
								pointerEvents: "none",
								position: "absolute",
								right: { xs: -120, md: -124 },
								top: { xs: -120, md: -74 },
								width: "100%",
								zIndex: 1,
							}}
						/>
						<Box
							component="img"
							src="/images/shape-v6-gpt-x-webflow-template.png"
							alt=""
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
										Please fill your email and password to sign in.
									</Typography>
								</Box>

								<Box component="form" onSubmit={handleSubmit} sx={{ mb: "24px" }}>
									<Box sx={{ mb: "32px" }}>
										<Typography
											component="label"
											htmlFor="email"
											sx={{
												color: neutrals.colors100,
												display: "block",
												fontSize: "18px",
												fontWeight: 500,
												lineHeight: "20px",
												mb: "12px",
											}}
										>
											Email
										</Typography>
										<Box
											component="input"
											type="email"
											id="email"
											name="email"
											value={email}
											onChange={(event) => setEmail(event.target.value)}
											placeholder="Email address"
											required
											sx={{
												backgroundColor: neutrals.colors700,
												border: `1px solid ${inputBorder}`,
												borderRadius: "20px",
												boxShadow: shadows[1],
												color: neutrals.colors100,
												fontSize: "18px",
												lineHeight: "30px",
												minHeight: "70px",
												outline: "none",
												p: "16px 24px",
												transition: "box-shadow 0.3s, color 0.3s, border-color 0.3s",
												width: "100%",
												"&::placeholder": {
													color: placeholderColor,
													fontSize: "18px",
													lineHeight: "30px",
												},
												"&:hover": {
													borderColor: neutrals.colors500,
													boxShadow: shadows[2],
												},
												"&:focus": {
													borderColor: neutrals.colors100,
													color: neutrals.colors100,
												},
											}}
										/>
									</Box>

									<Box sx={{ mb: "24px" }}>
										<Typography
											component="label"
											htmlFor="password"
											sx={{
												color: neutrals.colors100,
												display: "block",
												fontSize: "18px",
												fontWeight: 500,
												lineHeight: "20px",
												mb: "12px",
											}}
										>
											Password
										</Typography>
										<Box
											component="input"
											type="password"
											id="password"
											name="password"
											value={password}
											onChange={(event) => setPassword(event.target.value)}
											placeholder="Enter your password"
											required
											sx={{
												backgroundColor: neutrals.colors700,
												border: `1px solid ${inputBorder}`,
												borderRadius: "20px",
												boxShadow: shadows[1],
												color: neutrals.colors100,
												fontSize: "18px",
												lineHeight: "30px",
												minHeight: "70px",
												outline: "none",
												p: "16px 24px",
												transition: "box-shadow 0.3s, color 0.3s, border-color 0.3s",
												width: "100%",
												"&::placeholder": {
													color: placeholderColor,
													fontSize: "18px",
													lineHeight: "30px",
												},
												"&:hover": {
													borderColor: neutrals.colors500,
													boxShadow: shadows[2],
												},
												"&:focus": {
													borderColor: neutrals.colors100,
													color: neutrals.colors100,
												},
											}}
										/>
									</Box>

									<Box
										sx={{
											alignItems: "center",
											display: "flex",
											flexWrap: "wrap",
											gap: "16px",
											justifyContent: "space-between",
										}}
									>
										<Box
											component="label"
											sx={{ alignItems: "center", cursor: "pointer", display: "flex", gap: "8px", mb: 0 }}
										>
											<Box sx={{ position: "relative", width: 20, height: 20 }}>
												<Box
													component="input"
													type="checkbox"
													checked={rememberMe}
													onChange={(event) => setRememberMe(event.target.checked)}
													sx={{ inset: 0, opacity: 0, position: "absolute" }}
												/>
												<Box
													sx={{
														alignItems: "center",
														backgroundColor: neutrals.colors700,
														border: `1px solid ${neutrals.colors300}`,
														borderRadius: "4px",
														display: "flex",
														height: "20px",
														justifyContent: "center",
														transition: "all 0.2s",
														width: "20px",
														...(rememberMe && {
															backgroundColor: neutrals.colors100,
															borderColor: neutrals.colors100,
															"&::after": {
																color: palette.primary.main,
																content: '"✓"',
																fontSize: "12px",
																fontWeight: 700,
															},
														}),
													}}
												/>
											</Box>
											<Typography
												variant="body1"
												sx={{ color: neutrals.colors100, fontSize: "18px", lineHeight: "30px" }}
											>
												Remember me
											</Typography>
										</Box>
										<Link
											href="#"
											sx={{
												color: neutrals.colors100,
												fontSize: "18px",
												textDecoration: "underline",
												"&:hover": { color: neutrals.colors200 },
											}}
										>
											Forgot password?
										</Link>
									</Box>

									{/* Visually hidden submit so Enter key works without a visible primary button */}
									<Button
										type="submit"
										sx={{
											position: "absolute",
											width: 1,
											height: 1,
											p: 0,
											m: -1,
											overflow: "hidden",
											clip: "rect(0 0 0 0)",
											whiteSpace: "nowrap",
											border: 0,
										}}
									>
										Submit
									</Button>
								</Box>

								<Box sx={{ mb: "32px" }}>
									<Box sx={{ alignItems: "center", display: "flex" }}>
										{/* Full-width side dividers */}
										<Box sx={{ flex: 1, height: 0, borderTop: `1px solid ${dividerColor}` }} />
										{/* Center group with short dividers + OR badge */}
										<Box sx={{ alignItems: "center", display: "flex"  }}>

											<Box
												sx={{
													backgroundColor: neutrals.colors700,
													borderRadius: "8px",
													color: neutrals.colors100,
													fontSize: "18px",
													lineHeight: "1.111em",
													px: 2,
													py: 1.25,
													textAlign: "center",
													textTransform: "uppercase",
												}}
											>
												or
											</Box>

										</Box>
										{/* Full-width side dividers */}
										<Box sx={{ flex: 1, height: 0, borderTop: `1px solid ${dividerColor}` }} />
									</Box>
								</Box>

								<Box sx={{ mb: "32px" }}>
									<Link
										component="button"
										type="button"
										onClick={handleGoogleClick}
										sx={{
											alignItems: "center",
											backgroundColor: neutrals.colors700,
											border: `1px solid ${neutrals.colors300}`,
                      lineHeight: "1.111em",
											borderRadius: "16px",
											boxShadow: shadows[10],
											color: neutrals.colors100,
											display: "flex",
											fontSize: "18px",
											gap: "8px",
											justifyContent: "center",
											mb: "24px",
											p: "22px 16px",
											textDecoration: "none",
											transition: "all 0.3s",
											width: "100%",
											"&:hover": {
												borderColor: neutrals.colors100,
												color: neutrals.colors100,
												backgroundColor: "transparent",
											},
										}}
									>
										<Box
											component="img"
											src="/images/google-icon-gpt-x-webflow-template.svg"
											alt="Google Icon"
											sx={{ height: 20, width: 20 }}
										/>
										<Box sx={{ mt: "4px" }}>Sign in with Google</Box>
									</Link>

									<Link
										component="a"
										href="https://facebook.com"
										target="_blank"
										rel="noreferrer"
										sx={{
											alignItems: "center",
											backgroundColor: neutrals.colors700,
											border: `1px solid ${neutrals.colors300}`,
											borderRadius: "16px",
											boxShadow: shadows[10],
											color: neutrals.colors100,
                      lineHeight: "1.111em",
											display: "flex",
											fontSize: "18px",
											gap: "8px",
											justifyContent: "center",
											p: "22px 16px",
											textDecoration: "none",
											transition: "all 0.3s",
											width: "100%",
											"&:hover": {
												borderColor: neutrals.colors100,
												color: neutrals.colors100,
												backgroundColor: "transparent",
											},
										}}
									>
										<Box
											component="img"
											src="/images/facebook-icon-gpt-x-webflow-template.svg"
											alt="Facebook Icon"
											sx={{ height: 20, width: 20 }}
										/>
										<Box sx={{ mt: "4px" }}>Sign in with Facebook</Box>
									</Link>
								</Box>

								<Box sx={{ display: "flex", justifyContent: "center", textAlign: "center" }}>
									<Typography variant="body1" sx={{ color: neutrals.colors200 }}>
										Don&apos;t have an account?{" "}
										<Link
											href="#"
											sx={{
												color: neutrals.colors100,
												textDecoration: "underline",
												"&:hover": { color: neutrals.colors200 },
											}}
										>
											Sign up today
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
