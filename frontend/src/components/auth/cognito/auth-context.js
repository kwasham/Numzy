"use client";

import * as React from "react";
import { AuthProvider as OidcProvider } from "react-oidc-context";

import { createUserManager } from "@/lib/cognito/user-manager";

export function AuthProvider(props) {
	const userManager = createUserManager();

	return <OidcProvider userManager={userManager} skipSigninCallback {...props} />;
}
