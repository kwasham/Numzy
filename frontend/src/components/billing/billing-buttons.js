"use client";

import React from "react";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import Stack from "@mui/material/Stack";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const DEFAULT_PRICE = process.env.NEXT_PUBLIC_STRIPE_PRICE_PRO_MONTHLY || "";

async function postJson(path, body) {
	const res = await fetch(`${API_URL}${path}`, {
		method: "POST",
		headers: {
			"Content-Type": "application/json",
			// Optionally attach auth here if your app sets it in storage/cookies
		},
		body: JSON.stringify(body ?? {}),
		credentials: "include",
	});
	if (!res.ok) {
		const msg = await res.text();
		throw new Error(msg || `Request failed: ${res.status}`);
	}
	return res.json();
}

export function BillingButtons({ priceId = DEFAULT_PRICE, size = "medium" }) {
	const [loading, setLoading] = React.useState(null);

	const startCheckout = async () => {
		try {
			setLoading("checkout");
			const data = await postJson("/billing/checkout", { price_id: priceId });
			if (data?.url) globalThis.location.href = data.url;
		} catch (error) {
			console.error("Failed to start checkout", error);
			alert("Unable to start checkout. Please try again.");
		} finally {
			setLoading(null);
		}
	};

	const openPortal = async () => {
		try {
			setLoading("portal");
			const data = await postJson("/billing/portal");
			if (data?.url) globalThis.location.href = data.url;
		} catch (error) {
			console.error("Failed to open billing portal", error);
			alert("Unable to open billing portal. Please try again.");
		} finally {
			setLoading(null);
		}
	};

	return (
		<Stack direction="row" spacing={2} sx={{ alignItems: "center" }}>
			<Button
				variant="contained"
				color="primary"
				size={size}
				onClick={startCheckout}
				disabled={!priceId || loading === "checkout"}
			>
				{loading === "checkout" ? <CircularProgress size={18} /> : "Upgrade to Pro"}
			</Button>
			<Button variant="outlined" size={size} onClick={openPortal} disabled={loading === "portal"}>
				{loading === "portal" ? <CircularProgress size={18} /> : "Manage billing"}
			</Button>
		</Stack>
	);
}
