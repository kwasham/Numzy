"use client";

import * as React from "react";

import { createClient as createSupabaseClient } from "@/lib/supabase/browser";

export const AuthContext = React.createContext({
	isAuthenticated: false,
	isLoading: true,
	user: null,
});

export const AuthProvider = ({ children }) => {
	const [supabaseClient] = React.useState(createSupabaseClient());

	const [state, setState] = React.useState({
		isAuthenticated: false,
		isLoading: true,
		user: null,
	});

	React.useEffect(() => {
		const {
			data: { subscription },
		} = supabaseClient.auth.onAuthStateChange((_, session) => {
			setState((prevState) => ({
				...prevState,
				isAuthenticated: Boolean(session?.user),
				isLoading: false,
				user: session?.user ?? null,
			}));
		});

		return () => {
			subscription.unsubscribe();
		};
	}, [supabaseClient]);

	return <AuthContext.Provider value={{ ...state }}>{children}</AuthContext.Provider>;
};

export function useAuth() {
	const context = React.useContext(AuthContext);

	if (context === undefined) {
		throw new Error("useAuth must be used within an AuthProvider");
	}

	return context;
}
