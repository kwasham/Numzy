"use client";

import React from "react";
import { useAuth } from "@clerk/nextjs";
import Button from "@mui/material/Button";
import Grid from "@mui/material/Grid";
import Link from "@mui/material/Link";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

import { CreditCard } from "@/components/dashboard/crypto/credit-card";

type UnknownObject = Record<string, unknown>;
type ErrorInfo = { message: string; dashboardUrl?: string; pastDue?: string[] };

const ISSUING_REFRESH_EVENT = "numzy:issuing:refresh";

async function parseErrorInfo(res: Response): Promise<ErrorInfo> {
	try {
		const text = await res.text();
		if (text) {
			try {
				const body = JSON.parse(text) as unknown;
				if (typeof body === "object" && body !== null) {
					const obj = body as UnknownObject;
					// detail might be string or object with message/dashboard_url
					let message: string | undefined;
					let dashboardUrl: string | undefined;
					let pastDue: string[] | undefined;
					const detail = obj["detail"];
					if (typeof detail === "string") {
						message = detail;
					} else if (typeof detail === "object" && detail !== null) {
						const d = detail as UnknownObject;
						if (typeof d["message"] === "string") message = d["message"] as string;
						if (typeof d["dashboard_url"] === "string") dashboardUrl = d["dashboard_url"] as string;
						const pd = (d["past_due"] ?? d["pastDue"]) as unknown;
						if (Array.isArray(pd)) pastDue = pd.filter((x) => typeof x === "string") as string[];
					}
					if (!message && typeof obj["message"] === "string") message = obj["message"] as string;
					const err = obj["error"] as UnknownObject | undefined;
					if (!message && err && typeof err["message"] === "string") message = err["message"] as string;
					if (message) return { message, dashboardUrl, pastDue };
				}
			} catch {
				// Non-JSON response; fall through to status-based message.
			}
		}
	} catch {
		// Ignore body parsing errors; fall through to status-based message.
	}
	if (res.status === 401) return { message: "Sign in to manage virtual cards." };
	if (res.status === 400)
		return {
			message: "Stripe Issuing is not enabled for this account (test mode). Enable Issuing in your Stripe Dashboard.",
		};
	return { message: `Request failed (${res.status})` };
}

type CardSummary = {
	id: string;
	brand: string;
	last4: string;
	exp_month: number;
	exp_year: number;
	cardholderName?: string;
	status?: string;
};

export function IssuingCardsClient({ variant = "full" }: { variant?: "full" | "controls" | "list" }) {
	const { isSignedIn, getToken } = useAuth();
	const [cards, setCards] = React.useState<CardSummary[]>([]);
	const [error, setError] = React.useState<string | null>(null);
	const [dashboardUrl, setDashboardUrl] = React.useState<string | null>(null);
	const [pastDue, setPastDue] = React.useState<string[] | null>(null);
	const [loading, setLoading] = React.useState(false);

	const API_BASE = process.env.NEXT_PUBLIC_API_URL || process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

	const authHeaders = React.useCallback(async (): Promise<HeadersInit> => {
		if (!isSignedIn) return {};
		const token = await getToken();
		return token ? { Authorization: `Bearer ${token}` } : {};
	}, [isSignedIn, getToken]);

	const refresh = React.useCallback(async () => {
		setLoading(true);
		setError(null);
		setDashboardUrl(null);
		try {
			const headers = await authHeaders();
			const res = await fetch(`${API_BASE}/issuing/cards?limit=5`, { headers, cache: "no-store" });
			if (!res.ok) {
				const info = await parseErrorInfo(res);
				setError(info.message);
				setDashboardUrl(info.dashboardUrl || null);
				setPastDue(info.pastDue || null);
				setCards([]);
				return;
			}
			const data: CardSummary[] = await res.json();
			setCards(Array.isArray(data) ? data : []);
		} catch {
			setError("Unable to load cards. Check network and backend config.");
			setDashboardUrl(null);
			setPastDue(null);
			setCards([]);
		} finally {
			setLoading(false);
		}
	}, [API_BASE, authHeaders]);

	// List and full variants listen for global refresh events triggered by controls/actions
	React.useEffect(() => {
		if (variant === "controls") return;
		const handler = () => {
			void refresh();
		};
		globalThis.addEventListener(ISSUING_REFRESH_EVENT, handler as EventListener);
		return () => globalThis.removeEventListener(ISSUING_REFRESH_EVENT, handler as EventListener);
	}, [variant, refresh]);

	React.useEffect(() => {
		if (!isSignedIn) {
			setError("Sign in to manage virtual cards.");
			setDashboardUrl(null);
			setCards([]);
			return;
		}
		refresh();
	}, [isSignedIn, refresh]);

	const createDemo = async () => {
		setLoading(true);
		setError(null);
		setPastDue(null);
		setDashboardUrl(null);
		try {
			const headers = await authHeaders();
			const res = await fetch(`${API_BASE}/issuing/demo/create_virtual_card`, { method: "POST", headers });
			if (!res.ok) {
				const info = await parseErrorInfo(res);
				setError(info.message);
				setDashboardUrl(info.dashboardUrl || null);
				setPastDue(info.pastDue || null);
				return;
			}
			// Notify other component instances (e.g., list) to refresh immediately
			globalThis.dispatchEvent(new Event(ISSUING_REFRESH_EVENT));
		} catch {
			setError("Failed to create virtual card. Check network and backend config.");
			setDashboardUrl(null);
			setPastDue(null);
		} finally {
			setLoading(false);
		}
	};

	const toggleFreeze = async (id: string, status?: string) => {
		setLoading(true);
		setError(null);
		setPastDue(null);
		setDashboardUrl(null);
		try {
			const headers = await authHeaders();
			const path = status === "active" ? "freeze" : "unfreeze";
			const res = await fetch(`${API_BASE}/issuing/cards/${id}/${path}`, { method: "POST", headers });
			if (!res.ok) {
				const info = await parseErrorInfo(res);
				setError(info.message);
				setDashboardUrl(info.dashboardUrl || null);
				setPastDue(info.pastDue || null);
				return;
			}
			globalThis.dispatchEvent(new Event(ISSUING_REFRESH_EVENT));
		} catch {
			setError("Failed to update card status. Check network and backend config.");
			setDashboardUrl(null);
			setPastDue(null);
		} finally {
			setLoading(false);
		}
	};

	const testPurchase = async (id: string) => {
		setLoading(true);
		setError(null);
		setPastDue(null);
		setDashboardUrl(null);
		try {
			const headers = await authHeaders();
			const res = await fetch(`${API_BASE}/issuing/cards/${id}/test_purchase`, {
				method: "POST",
				headers: { ...headers, "Content-Type": "application/json" },
				body: JSON.stringify({ amount: 500, currency: "usd", merchant_name: "Numzy Test", auto_capture: true }),
			});
			if (!res.ok) {
				const info = await parseErrorInfo(res);
				setError(info.message);
				setDashboardUrl(info.dashboardUrl || null);
				setPastDue(info.pastDue || null);
				return;
			}
			globalThis.dispatchEvent(new Event(ISSUING_REFRESH_EVENT));
		} catch {
			setError("Failed to simulate test purchase. Check Stripe test helpers and Issuing balance.");
			setDashboardUrl(null);
			setPastDue(null);
		} finally {
			setLoading(false);
		}
	};

	const fixRequirements = async (id: string) => {
		setLoading(true);
		setError(null);
		setPastDue(null);
		setDashboardUrl(null);
		try {
			const headers = await authHeaders();
			const res = await fetch(`${API_BASE}/issuing/cards/${id}/fix_requirements`, { method: "POST", headers });
			if (!res.ok) {
				const info = await parseErrorInfo(res);
				setError(info.message);
				setDashboardUrl(info.dashboardUrl || null);
				setPastDue(info.pastDue || null);
				return;
			}
			globalThis.dispatchEvent(new Event(ISSUING_REFRESH_EVENT));
		} catch {
			setError("Failed to fix cardholder requirements.");
			setDashboardUrl(null);
			setPastDue(null);
		} finally {
			setLoading(false);
		}
	};

	const Controls = (
		<Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
			<Button onClick={createDemo} disabled={!isSignedIn || loading} variant="contained" size="small">
				Create virtual card
			</Button>
			<Button
				onClick={() => {
					// broadcast-only; list/full listeners will fetch
					globalThis.dispatchEvent(new Event(ISSUING_REFRESH_EVENT));
				}}
				disabled={!isSignedIn || loading}
				size="small"
				variant="outlined"
			>
				Refresh
			</Button>
		</Stack>
	);

	const List = (
		<Grid container spacing={2}>
			{cards.length === 0 && isSignedIn && !loading ? (
				<Grid item xs={12}>
					<Typography variant="body2" color="text.secondary">
						No virtual cards yet. Use &ldquo;Create virtual card&rdquo; to add your first one.
					</Typography>
				</Grid>
			) : null}
			{cards.map((c) => (
				<Grid key={c.id} item xs={12} md={6} xl={4}>
					<Stack spacing={1}>
						<CreditCard
							card={{
								id: c.id,
								brand: c.brand,
								last4: c.last4,
								exp_month: c.exp_month,
								exp_year: c.exp_year,
								cardholderName: c.cardholderName,
							}}
						/>
						<Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
							<Button onClick={() => toggleFreeze(c.id, c.status)} size="small" variant="outlined">
								{c.status === "active" ? "Freeze" : "Unfreeze"}
							</Button>
							<Button onClick={() => fixRequirements(c.id)} size="small" variant="outlined">
								Fix requirements
							</Button>
							<Button onClick={() => testPurchase(c.id)} size="small" variant="outlined">
								Test $5 purchase
							</Button>
							<Typography variant="caption" color="text.secondary">
								Status: {c.status || "unknown"}
							</Typography>
						</Stack>
					</Stack>
				</Grid>
			))}
		</Grid>
	);

	if (variant === "controls") {
		return (
			<Stack spacing={1}>
				{error ? (
					<Stack spacing={0.5}>
						<Typography variant="body2" color="text.secondary">
							{error}
						</Typography>
						{pastDue && pastDue.length > 0 ? (
							<Typography variant="caption" color="text.secondary">
								Missing: {pastDue.slice(0, 5).join(", ")}
							</Typography>
						) : null}
						{dashboardUrl ? (
							<Link href={dashboardUrl} target="_blank" rel="noreferrer" underline="hover" variant="caption">
								Open in Stripe Dashboard
							</Link>
						) : null}
					</Stack>
				) : null}
				{Controls}
			</Stack>
		);
	}

	if (variant === "list") {
		return (
			<Stack spacing={2}>
				{error ? (
					<Stack spacing={0.5}>
						<Typography variant="body2" color="text.secondary">
							{error}
						</Typography>
						{pastDue && pastDue.length > 0 ? (
							<Typography variant="caption" color="text.secondary">
								Missing: {pastDue.slice(0, 5).join(", ")}
							</Typography>
						) : null}
						{dashboardUrl ? (
							<Link href={dashboardUrl} target="_blank" rel="noreferrer" underline="hover" variant="caption">
								Open in Stripe Dashboard
							</Link>
						) : null}
					</Stack>
				) : null}
				{List}
			</Stack>
		);
	}

	// full
	return (
		<Stack spacing={2}>
			{error ? (
				<Stack spacing={0.5}>
					<Typography variant="body2" color="text.secondary">
						{error}
					</Typography>
					{pastDue && pastDue.length > 0 ? (
						<Typography variant="caption" color="text.secondary">
							Missing: {pastDue.slice(0, 5).join(", ")}
						</Typography>
					) : null}
					{dashboardUrl ? (
						<Link href={dashboardUrl} target="_blank" rel="noreferrer" underline="hover" variant="caption">
							Open in Stripe Dashboard
						</Link>
					) : null}
				</Stack>
			) : null}
			{Controls}
			{List}
		</Stack>
	);
}
