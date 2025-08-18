"use client";

import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useAuth } from "@clerk/nextjs";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CircularProgress from "@mui/material/CircularProgress";
import Container from "@mui/material/Container";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Stack from "@mui/material/Stack";
import { useTheme } from "@mui/material/styles";
import Typography from "@mui/material/Typography";
import { Elements, PaymentElement, PaymentRequestButtonElement, useElements, useStripe } from "@stripe/react-stripe-js";
import { loadStripe } from "@stripe/stripe-js";

// Types for catalog
type CatalogEntry = { name: string; currency: string; price: number; price_id: string | null };
type Catalog = Record<string, CatalogEntry>;

const stripePromise = loadStripe(process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY as string);
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function SubscribePage() {
	const { getToken } = useAuth();
	const searchParams = useSearchParams();
	const muiTheme = useTheme();
	const [catalog, setCatalog] = useState<Catalog>({});
	const [currentPlan, setCurrentPlan] = useState<string>("startup");
	const [selected, setSelected] = useState<string>("standard");
	const [clientSecret, setClientSecret] = useState<string | null>(null);
	const [loading, setLoading] = useState<boolean>(true);
	const [isDark, setIsDark] = useState<boolean>(() => {
		let classDark = false;
		if (typeof document === "object" && document?.documentElement) {
			const root = document.documentElement;
			const attr = root.dataset.muiColorScheme || root.dataset.colorScheme || document.body?.dataset?.theme;
			classDark = root.classList?.contains?.("dark") ?? false;
			if (attr === "dark" || classDark) return true;
			if (attr === "light") return false;
		}
		const mode = muiTheme?.palette?.mode as "light" | "dark" | undefined;
		if (mode) return mode === "dark";
		const hasMM = typeof globalThis.matchMedia === "function";
		if (hasMM) {
			return globalThis.matchMedia("(prefers-color-scheme: dark)").matches;
		}
		return false;
	});

	// Update when MUI theme mode changes
	useEffect(() => {
		if (typeof document === "object" && document?.documentElement) {
			const root = document.documentElement;
			const attr = root.dataset.muiColorScheme || root.dataset.colorScheme || document.body?.dataset?.theme;
			const classDark = root.classList?.contains?.("dark") ?? false;
			if (attr === "dark" || classDark) {
				setIsDark(true);
				return;
			}
			if (attr === "light") {
				setIsDark(false);
				return;
			}
		}
		const mode = muiTheme?.palette?.mode as "light" | "dark" | undefined;
		if (mode) setIsDark(mode === "dark");
	}, [muiTheme]);

	// Listen to OS scheme changes if MUI mode is not provided
	useEffect(() => {
		if (typeof globalThis === "undefined" || !globalThis.matchMedia) return;
		const mode = muiTheme?.palette?.mode as "light" | "dark" | undefined;
		if (mode) return; // MUI drives it
		const mql = globalThis.matchMedia("(prefers-color-scheme: dark)");
		const handler = (e: MediaQueryListEvent) => setIsDark(e.matches);
		try {
			mql.addEventListener("change", handler);
			return () => mql.removeEventListener("change", handler);
		} catch {
			// Safari fallback
			// @ts-expect-error legacy Safari
			mql.addListener(handler);
			// @ts-expect-error legacy Safari
			return () => mql.removeListener(handler);
		}
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, []);

	useEffect(() => {
		let ignore = false;
		(async () => {
			try {
				const jwt = await getToken();
				const res = await fetch(`${API_URL}/billing/status`, {
					headers: jwt ? { Authorization: `Bearer ${jwt}` } : undefined,
					cache: "no-store",
				});
				const data = await res.json();
				if (!ignore) {
					setCatalog(data.catalog || {});
					setCurrentPlan(data.plan || "FREE");
				}
			} catch {
				// noop
			} finally {
				if (!ignore) setLoading(false);
			}
		})();
		return () => {
			ignore = true;
		};
	}, [getToken]);

	const options = useMemo(() => {
		const commonVars = { fontFamily: "inherit", borderRadius: "8px", spacingUnit: "4px" } as const;
		const appearance = isDark
			? {
					theme: "night" as const,
					variables: {
						...commonVars,
						colorPrimary: "#7aa2ff",
						colorPrimaryText: "#E6E6E6",
						colorBackground: "#0B0F19",
						colorBackgroundSecondary: "#0F1524",
						colorText: "#E6E6E6",
						colorTextSecondary: "#B0B8C4",
						colorIcon: "#9AA2AF",
						colorDanger: "#ef5350",
						colorSuccess: "#66bb6a",
						colorBorder: "#22304A",
					},
					rules: {
						".Block": { backgroundColor: "transparent", borderColor: "#22304A" },
						".Block:hover": { borderColor: "#2C3E63" },
						".Input": { backgroundColor: "transparent", color: "#E6E6E6" },
						".Input--empty": { backgroundColor: "transparent", color: "#E6E6E6" },
						".Input:focus": { backgroundColor: "#0B0F19", borderColor: "#2C3E63" },
						".Input--invalid": { borderColor: "#ef5350" },
						".Input::placeholder": { color: "#9AA2AF" },
						".Label": { color: "#B0B8C4" },
						".Tab": { backgroundColor: "#0B0F19", color: "#E6E6E6" },
						".Tab:hover": { backgroundColor: "#111829" },
						".Tab--selected": { backgroundColor: "#111829", borderColor: "#2C3E63" },
						".TabLabel": { color: "#E6E6E6" },
						".Radio, .Checkbox": { color: "#E6E6E6" },
						".Divider": { color: "#22304A" },
						".Picker": { backgroundColor: "#0B0F19", color: "#E6E6E6", borderColor: "#22304A" },
						".PickerItem": { color: "#E6E6E6" },
						".PickerItem--selected": { backgroundColor: "#111829" },
					},
				}
			: {
					theme: "stripe" as const,
					variables: { ...commonVars },
				};

		return { appearance, clientSecret: clientSecret || undefined, loader: "auto" as const };
	}, [clientSecret, isDark]);

	const handlePlanChange = (value: string) => setSelected(value);

	const initPayment = async () => {
		const entry = catalog[selected];
		if (!entry?.price_id) return;
		const jwt = await getToken();
		const idempotency = globalThis?.crypto?.randomUUID?.() || `${Date.now()}-${Math.random()}`;
		const res = await fetch(`${API_URL}/billing/elements/init`, {
			method: "POST",
			headers: {
				"Content-Type": "application/json",
				"Idempotency-Key": idempotency,
				...(jwt ? { Authorization: `Bearer ${jwt}` } : {}),
			},
			body: JSON.stringify({ price_id: entry.price_id }),
		});
		if (!res.ok) throw new Error("Failed to initialize payment");
		const data = await res.json();
		setClientSecret(data.client_secret);
	};

	// Preselect plan from query string if provided
	useEffect(() => {
		const qp = searchParams?.get("plan");
		if (qp) setSelected(qp);
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, []);

	return (
		<main>
			<Container maxWidth="sm" sx={{ py: 6 }}>
				<Stack spacing={3}>
					<Typography variant="h4">Subscribe</Typography>
					<Card variant="outlined" sx={{ p: 3 }}>
						{loading ? (
							<Box sx={{ display: "flex", justifyContent: "center" }}>
								<CircularProgress size={24} />
							</Box>
						) : (
							<Stack spacing={2}>
								<Stack spacing={1}>
									<Typography variant="subtitle2">Choose a plan</Typography>
									{Object.keys(catalog).length > 0 ? (
										<Select value={selected} onChange={(e) => handlePlanChange(String(e.target.value))}>
											{Object.entries(catalog).map(([key, v]) => (
												<MenuItem key={key} value={key} disabled={!v.price_id}>
													{v.name} —{" "}
													{new Intl.NumberFormat("en-US", { style: "currency", currency: v.currency }).format(v.price)}{" "}
													/ mo
													{currentPlan && key.toLowerCase().includes(currentPlan.toString().toLowerCase())
														? " (Current)"
														: ""}
												</MenuItem>
											))}
										</Select>
									) : (
										<Typography color="text.secondary" variant="body2">
											No plans available. Please ensure you are signed in and try again.
										</Typography>
									)}
								</Stack>
								{clientSecret ? (
									<Elements
										stripe={stripePromise}
										options={options}
										// Force remount when theme changes so appearance applies inside iframes
										key={`elements-${isDark ? "dark" : "light"}-${clientSecret}`}
									>
										<ExpressCheckout
											amountCents={Math.round((catalog[selected]?.price || 0) * 100)}
											currency={(catalog[selected]?.currency || "USD").toLowerCase()}
											label={`Numzy — ${catalog[selected]?.name || "Subscription"} (monthly)`}
											isDark={isDark}
										/>
										<Typography
											variant="caption"
											color="text.secondary"
											sx={{ display: "block", textAlign: "center", my: 1 }}
										>
											or pay with card
										</Typography>
										<CheckoutForm />
									</Elements>
								) : (
									<Button variant="contained" onClick={initPayment} disabled={!catalog[selected]?.price_id}>
										Continue to payment
									</Button>
								)}
							</Stack>
						)}
					</Card>
				</Stack>
			</Container>
		</main>
	);
}

function CheckoutForm() {
	const stripe = useStripe();
	const elements = useElements();
	const [submitting, setSubmitting] = useState(false);

	const handleSubmit = async () => {
		if (!stripe || !elements) return;
		setSubmitting(true);
		const { error } = await stripe.confirmPayment({
			elements,
			confirmParams: {
				return_url: `${process.env.NEXT_PUBLIC_FRONTEND_URL || globalThis.location.origin}/dashboard?checkout=success`,
			},
		});
		if (error) {
			// minimal UX; page already holds state, user can retry
			console.error(error);
		}
		setSubmitting(false);
	};

	return (
		<Stack spacing={2}>
			<PaymentElement options={{ layout: "tabs" }} />
			<Button variant="contained" onClick={handleSubmit} disabled={submitting}>
				{submitting ? "Processing…" : "Pay"}
			</Button>
		</Stack>
	);
}

function ExpressCheckout({
	amountCents,
	currency,
	label,
	isDark,
}: {
	amountCents: number;
	currency: string;
	label: string;
	isDark: boolean;
}) {
	const stripe = useStripe();
	const elements = useElements();
	const [pr, setPr] = useState<unknown | null>(null);
	const [methods, setMethods] = useState<Record<string, boolean> | null>(null);

	useEffect(() => {
		if (!stripe || !elements || !amountCents || !currency) return;
		const paymentRequest = stripe.paymentRequest({
			country: "US",
			currency,
			total: { label, amount: amountCents },
			requestPayerEmail: true,
		});
		paymentRequest.canMakePayment().then((result) => {
			if (result) {
				setPr(paymentRequest);
				setMethods(result as unknown as Record<string, boolean>);
			}
		});
		return () => {
			try {
				paymentRequest?.off?.("paymentmethod", () => {});
			} catch (error) {
				console.error(error);
			}
		};
	}, [stripe, elements, amountCents, currency, label]);

	if (!stripe || !pr) return null;

	const hint = methods?.applePay
		? "Fast checkout with Apple Pay"
		: methods?.googlePay
			? "Fast checkout with Google Pay"
			: methods?.link
				? "Fast checkout with Link"
				: "Fast checkout";

	// The PaymentRequest type isn't exported directly; cast through unknown to satisfy TS
	return (
		<Box sx={{ mb: 2 }}>
			<Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 1 }}>
				{hint}
			</Typography>
			<PaymentRequestButtonElement
				options={{
					paymentRequest: pr as unknown as never,
					style: { paymentRequestButton: { height: "44px", theme: isDark ? "dark" : "light", type: "buy" } },
				}}
			/>
		</Box>
	);
}
