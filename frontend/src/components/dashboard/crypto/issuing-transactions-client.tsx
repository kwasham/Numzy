"use client";

import React from "react";
import { useAuth } from "@clerk/nextjs";
import Avatar from "@mui/material/Avatar";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import CardHeader from "@mui/material/CardHeader";
import Link from "@mui/material/Link";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemAvatar from "@mui/material/ListItemAvatar";
import ListItemText from "@mui/material/ListItemText";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import { ArrowsDownUpIcon } from "@phosphor-icons/react/dist/ssr/ArrowsDownUp";
import { TrendDownIcon } from "@phosphor-icons/react/dist/ssr/TrendDown";
import { TrendUpIcon } from "@phosphor-icons/react/dist/ssr/TrendUp";

type UnknownObject = Record<string, unknown>;
type ErrorInfo = { message: string; dashboardUrl?: string };

const ISSUING_REFRESH_EVENT = "numzy:issuing:refresh";

async function parseErrorInfo(res: Response): Promise<ErrorInfo> {
	try {
		const text = await res.text();
		if (text) {
			try {
				const body = JSON.parse(text) as unknown;
				if (typeof body === "object" && body !== null) {
					const obj = body as UnknownObject;
					let message: string | undefined;
					let dashboardUrl: string | undefined;
					const detail = obj["detail"];
					if (typeof detail === "string") {
						message = detail;
					} else if (typeof detail === "object" && detail !== null) {
						const d = detail as UnknownObject;
						if (typeof d["message"] === "string") message = d["message"] as string;
						if (typeof d["dashboard_url"] === "string") dashboardUrl = d["dashboard_url"] as string;
					}
					if (!message && typeof obj["message"] === "string") message = obj["message"] as string;
					const err = obj["error"] as UnknownObject | undefined;
					if (!message && err && typeof err["message"] === "string") message = err["message"] as string;
					if (message) return { message, dashboardUrl };
				}
			} catch {
				// ignore
			}
		}
	} catch {
		// ignore parsing errors
	}
	if (res.status === 401) return { message: "Sign in to view transactions." };
	return { message: `Request failed (${res.status})` };
}

type IssuingTxn = {
	id: string;
	amount: number; // minor units
	currency: string;
	merchant_name?: string;
	status?: string;
	type?: string; // capture/refund/etc
	created?: number; // epoch seconds
};

function formatAmount(minor: number, currency: string) {
	const val = (minor || 0) / 100;
	try {
		return new Intl.NumberFormat("en-US", { style: "currency", currency: (currency || "USD").toUpperCase() }).format(
			val
		);
	} catch {
		return `$${val.toFixed(2)}`;
	}
}

export function IssuingTransactionsClient({ limit = 10 }: { limit?: number }) {
	const { isSignedIn, getToken } = useAuth();
	const [txns, setTxns] = React.useState<IssuingTxn[]>([]);
	const [error, setError] = React.useState<string | null>(null);
	const [dashboardUrl, setDashboardUrl] = React.useState<string | null>(null);
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
			const res = await fetch(`${API_BASE}/issuing/transactions?limit=${encodeURIComponent(String(limit))}`, {
				headers,
				cache: "no-store",
			});
			if (!res.ok) {
				const info = await parseErrorInfo(res);
				setError(info.message);
				setDashboardUrl(info.dashboardUrl || null);
				setTxns([]);
				return;
			}
			const data: IssuingTxn[] = await res.json();
			setTxns(Array.isArray(data) ? data : []);
		} catch {
			setError("Unable to load transactions. Check network and backend config.");
			setDashboardUrl(null);
			setTxns([]);
		} finally {
			setLoading(false);
		}
	}, [API_BASE, limit, authHeaders]);

	React.useEffect(() => {
		if (!isSignedIn) {
			setError("Sign in to view transactions.");
			setDashboardUrl(null);
			setTxns([]);
			return;
		}
		void refresh();
	}, [isSignedIn, refresh]);

	React.useEffect(() => {
		const handler = () => void refresh();
		globalThis.addEventListener(ISSUING_REFRESH_EVENT, handler as EventListener);
		return () => globalThis.removeEventListener(ISSUING_REFRESH_EVENT, handler as EventListener);
	}, [refresh]);

	return (
		<Card>
			<CardHeader
				avatar={
					<Avatar>
						<ArrowsDownUpIcon fontSize="var(--Icon-fontSize)" />
					</Avatar>
				}
				title="Issuing Transactions"
				subheader={loading ? "Loading…" : undefined}
			/>
			{error ? (
				<CardContent>
					<Stack spacing={0.5}>
						<Typography variant="body2" color="text.secondary">
							{error}
						</Typography>
						{dashboardUrl ? (
							<Link href={dashboardUrl} target="_blank" rel="noreferrer" underline="hover" variant="caption">
								Open in Stripe Dashboard
							</Link>
						) : null}
					</Stack>
				</CardContent>
			) : null}
			<List disablePadding sx={{ "& .MuiListItem-root": { py: 2 } }}>
				{txns.length === 0 && !loading ? (
					<ListItem>
						<ListItemText
							primary={<Typography variant="body2">No transactions yet.</Typography>}
							secondary={
								<Typography variant="caption" color="text.secondary">
									Create a test purchase to see it here.
								</Typography>
							}
						/>
					</ListItem>
				) : null}
				{txns.map((t) => {
					const isCredit = (t.type || "").toLowerCase().includes("refund");
					const iconColorBg = isCredit ? "var(--mui-palette-success-50)" : "var(--mui-palette-error-50)";
					const iconColorFg = isCredit ? "var(--mui-palette-success-main)" : "var(--mui-palette-error-main)";
					const created = t.created ? new Date((t.created || 0) * 1000) : new Date();
					return (
						<ListItem divider key={t.id}>
							<ListItemAvatar>
								<Avatar sx={{ bgcolor: iconColorBg, color: iconColorFg }}>
									{isCredit ? (
										<TrendUpIcon fontSize="var(--Icon-fontSize)" />
									) : (
										<TrendDownIcon fontSize="var(--Icon-fontSize)" />
									)}
								</Avatar>
							</ListItemAvatar>
							<ListItemText
								disableTypography
								primary={<Typography variant="subtitle2">{t.merchant_name || "Transaction"}</Typography>}
								secondary={
									<Typography color="text.secondary" variant="body2">
										{created.toLocaleString()} • {t.status || "pending"}
									</Typography>
								}
							/>
							<div>
								<Typography color={iconColorFg} sx={{ textAlign: "right", whiteSpace: "nowrap" }} variant="subtitle2">
									{isCredit ? "+" : "-"} {formatAmount(t.amount, t.currency)}
								</Typography>
							</div>
						</ListItem>
					);
				})}
			</List>
		</Card>
	);
}
