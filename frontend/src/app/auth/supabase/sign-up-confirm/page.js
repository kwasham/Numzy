import * as React from "react";
import RouterLink from "next/link";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

import { appConfig } from "@/config/app";
import { paths } from "@/paths";
import { SplitLayout } from "@/components/auth/split-layout";
import { SignUpResendButton } from "@/components/auth/supabase/sign-up-resend-button";
import { DynamicLogo } from "@/components/core/logo";

export const metadata = { title: `Sign up confirm | Supabase | Auth | ${appConfig.name}` };

export default async function Page({ searchParams }) {
	const { email } = await searchParams;

	if (!email) {
		return (
			<Box sx={{ p: 3 }}>
				<Alert color="error">Email is required</Alert>
			</Box>
		);
	}

	return (
		<SplitLayout>
			<Stack spacing={4}>
				<div>
					<Box component={RouterLink} href={paths.home} sx={{ display: "inline-block", fontSize: 0 }}>
						<DynamicLogo colorDark="light" colorLight="dark" height={32} width={122} />
					</Box>
				</div>
				<Typography variant="h5">Confirm your email</Typography>
				<Typography>
					We&apos;ve sent a verification email to{" "}
					<Typography component="span" variant="subtitle1">
						&quot;{email}&quot;
					</Typography>
					.
				</Typography>
				<SignUpResendButton email={email}>Resend</SignUpResendButton>
			</Stack>
		</SplitLayout>
	);
}
