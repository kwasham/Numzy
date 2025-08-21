"use client";

import React from "react";
import { useAuth } from "@clerk/nextjs";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import { Elements, PaymentElement, useElements, useStripe } from "@stripe/react-stripe-js";
import { loadStripe } from "@stripe/stripe-js";

const stripePromise = loadStripe(process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY || "");
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function PaymentRecoveryDialog({ open, onClose }) {
	const { getToken } = useAuth();
	const [loading, setLoading] = React.useState(false);
	const [clientSecret, setClientSecret] = React.useState(null);
	const [error, setError] = React.useState(null);

	// Fetch status to learn subscription/action details, then fetch PI client secret
	const hydrate = React.useCallback(async () => {
		setError(null);
		setClientSecret(null);
		setLoading(true);
		try {
			const token = (await getToken?.()) || null;
			const statusRes = await fetch(`${API_URL}/billing/status`, {
				headers: token ? { Authorization: `Bearer ${token}` } : undefined,
				cache: "no-store",
			});
			const status = await statusRes.json();
			const subId = status?.subscription?.id || null;
			const invoiceId = status?.action?.invoice_id || null;
			if (!subId && !invoiceId) throw new Error("No subscription or invoice found");

			const qs = new URLSearchParams();
			if (subId) qs.set("subscription_id", subId);
			if (invoiceId) qs.set("invoice_id", invoiceId);
			const piRes = await fetch(`${API_URL}/billing/payment-intent?${qs.toString()}`, {
				headers: token ? { Authorization: `Bearer ${token}` } : undefined,
			});
			if (!piRes.ok) throw new Error(`Failed to fetch client_secret (${piRes.status})`);
			const data = await piRes.json();
			setClientSecret(data.client_secret);
		} catch {
			setError("Unable to initialize payment. Please try again or use the billing portal.");
		} finally {
			setLoading(false);
		}
	}, [getToken]);

	React.useEffect(() => {
		if (open) hydrate();
	}, [open, hydrate]);

	return (
		<Dialog open={open} onClose={onClose} fullWidth maxWidth="sm">
			<DialogTitle>Fix your payment</DialogTitle>
			<DialogContent>
				{loading && (
					<Stack sx={{ alignItems: "center", py: 3 }}>
						<CircularProgress size={24} />
					</Stack>
				)}
				{error && (
					<Typography color="error" variant="body2" sx={{ mb: 2 }}>
						{error}
					</Typography>
				)}
				{clientSecret && (
					<Elements stripe={stripePromise} options={{ clientSecret }}>
						<CheckoutInner onClose={onClose} />
					</Elements>
				)}
			</DialogContent>
			<DialogActions>
				<PortalButton />
				<Button onClick={onClose}>Close</Button>
			</DialogActions>
		</Dialog>
	);
}

function PortalButton() {
	const { getToken } = useAuth();
	const [busy, setBusy] = React.useState(false);

	const openPortal = async () => {
		try {
			setBusy(true);
			const token = (await getToken?.()) || null;
			const res = await fetch(`${API_URL}/billing/portal`, {
				method: "POST",
				headers: {
					"Content-Type": "application/json",
					...(token ? { Authorization: `Bearer ${token}` } : {}),
				},
			});
			const data = await res.json();
			if (data?.url) globalThis.location.href = data.url;
		} finally {
			setBusy(false);
		}
	};

	return (
		<Button onClick={openPortal} disabled={busy} variant="outlined">
			{busy ? <CircularProgress size={18} /> : "Manage in portal"}
		</Button>
	);
}

function CheckoutInner({ onClose }) {
	const stripe = useStripe();
	const elements = useElements();
	const { getToken } = useAuth();
	const [submitting, setSubmitting] = React.useState(false);
	const [err, setErr] = React.useState(null);

	const onSubmit = async () => {
		if (!stripe || !elements) return;
		setSubmitting(true);
		setErr(null);
		const result = await stripe.confirmPayment({
			elements,
			redirect: "if_required",
			confirmParams: {
				return_url: `${process.env.NEXT_PUBLIC_FRONTEND_URL || globalThis.location.origin}/dashboard?checkout=success`,
			},
		});

		if (result.error) {
			setErr(result.error.message || "Payment failed");
			setSubmitting(false);
			return;
		}

		// If succeeded and we know the PM id, set as default for sub
		try {
			const token = (await getToken?.()) || null;
			const intent = result.paymentIntent;
			const pmId = intent?.payment_method || null;
			if (pmId) {
				// Best-effort: we still need the subscription id; refetch status quickly
				const statusRes = await fetch(`${API_URL}/billing/status`, {
					headers: token ? { Authorization: `Bearer ${token}` } : undefined,
					cache: "no-store",
				});
				const status = await statusRes.json();
				const subId = status?.subscription?.id || null;
				const invId = status?.action?.invoice_id || null;
				if (subId) {
					await fetch(`${API_URL}/billing/subscription/payment-method`, {
						method: "POST",
						headers: {
							"Content-Type": "application/json",
							...(token ? { Authorization: `Bearer ${token}` } : {}),
						},
						body: JSON.stringify({ subscription_id: subId, payment_method_id: pmId, invoice_id: invId || null }),
					});
				}
			}
		} catch {
			// best-effort, ignore
		}

		setSubmitting(false);
		onClose?.();
		// Encourage a status refresh after a short delay
		try {
			globalThis.sessionStorage?.setItem("numzy_plan_refresh_until", String(Date.now() + 60_000));
		} catch {
			// ignore
		}
		globalThis.location.reload();
	};

	return (
		<Stack spacing={2} sx={{ py: 1 }}>
			<PaymentElement options={{ layout: "tabs" }} />
			{err ? (
				<Typography color="error" variant="body2">
					{err}
				</Typography>
			) : null}
			<Button onClick={onSubmit} disabled={submitting} variant="contained">
				{submitting ? "Processing…" : "Pay now"}
			</Button>
		</Stack>
	);
}
