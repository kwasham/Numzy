import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Grid from "@mui/material/Grid";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import { ArrowRightIcon } from "@phosphor-icons/react/dist/ssr/ArrowRight";
import { BriefcaseIcon } from "@phosphor-icons/react/dist/ssr/Briefcase";
import { FileCodeIcon } from "@phosphor-icons/react/dist/ssr/FileCode";
import { InfoIcon } from "@phosphor-icons/react/dist/ssr/Info";
import { ListChecksIcon } from "@phosphor-icons/react/dist/ssr/ListChecks";
import { PlusIcon } from "@phosphor-icons/react/dist/ssr/Plus";
import { UsersIcon } from "@phosphor-icons/react/dist/ssr/Users";
import { WarningIcon } from "@phosphor-icons/react/dist/ssr/Warning";

import { appConfig } from "@/config/app";
import { DunningEntrypoint } from "@/components/billing/dunning-entrypoint";
import { PlanBadge } from "@/components/billing/plan-badge";
import { TrialBanner } from "@/components/billing/trial-banner";
import { AppChatClient } from "@/components/dashboard/overview/app-chat-client";
import { AppLimits } from "@/components/dashboard/overview/app-limits";
import { AppUsage } from "@/components/dashboard/overview/app-usage";
import { CheckoutReturnNotifier } from "@/components/dashboard/overview/checkout-return-notifier";
import { EventsClient } from "@/components/dashboard/overview/events-client";
import { HelperWidget } from "@/components/dashboard/overview/helper-widget";
import { Subscriptions } from "@/components/dashboard/overview/subscriptions";
import { Summary } from "@/components/dashboard/overview/summary";

export const metadata = { title: `Overview | Dashboard | ${appConfig.name}` };

// Revalidate metrics periodically to keep the UI fresh without live polling.
export const revalidate = 60;
// In development, avoid caching to reflect backend changes immediately.
export const dynamic = "force-dynamic";
const isProd = process.env.NODE_ENV === "production";
const cacheOptions = isProd ? { next: { revalidate } } : { cache: "no-store" };

async function fetchSummary(headers = {}) {
	const API_BASE = process.env.NEXT_PUBLIC_API_URL || process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
	const controller = new AbortController();
	const timer = setTimeout(() => controller.abort(), 2500);
	try {
		const res = await fetch(`${API_BASE}/metrics/summary`, { ...cacheOptions, headers, signal: controller.signal });
		if (!res.ok) throw new Error(`summary ${res.status}`);
		const json = await res.json();
		return {
			processed24h: Number(json.processed24h ?? 0),
			processedPrev24h: Number(json.processedPrev24h ?? 0),
			avgAccuracy7d: Number(json.avgAccuracy7d ?? Number.NaN),
			avgAccuracyPrev7d: Number(json.avgAccuracyPrev7d ?? Number.NaN),
			openAudits: Number(json.openAudits ?? 0),
		};
	} catch {
		return {
			processed24h: 0,
			processedPrev24h: 0,
			avgAccuracy7d: Number.NaN,
			avgAccuracyPrev7d: Number.NaN,
			openAudits: 0,
		};
	} finally {
		clearTimeout(timer);
	}
}

async function fetchAppUsage(headers = {}) {
	const API_BASE = process.env.NEXT_PUBLIC_API_URL || process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
	const controller = new AbortController();
	const timer = setTimeout(() => controller.abort(), 2500);
	try {
		const res = await fetch(`${API_BASE}/metrics/app/usage?window=12m&bucket=month`, {
			...cacheOptions,
			headers,
			signal: controller.signal,
		});
		if (!res.ok) throw new Error(`usage ${res.status}`);
		const rows = await res.json();
		// Expecting rows like [{ ts: "2025-01-01", dau: 36, requests: 19 }, ...]
		const formatter = new Intl.DateTimeFormat(undefined, { month: "short" });
		return rows.map((r) => {
			const d = new Date(r.ts);
			return {
				name: formatter.format(d),
				v1: Number(r.dau ?? 0),
				v2: Number(r.requests ?? 0),
			};
		});
	} catch {
		// Fallback to existing static shape so UI stays useful
		return [
			{ name: "Jan", v1: 36, v2: 19 },
			{ name: "Feb", v1: 45, v2: 23 },
			{ name: "Mar", v1: 26, v2: 12 },
			{ name: "Apr", v1: 39, v2: 20 },
			{ name: "May", v1: 26, v2: 12 },
			{ name: "Jun", v1: 42, v2: 31 },
			{ name: "Jul", v1: 38, v2: 19 },
			{ name: "Aug", v1: 39, v2: 20 },
			{ name: "Sep", v1: 37, v2: 18 },
			{ name: "Oct", v1: 41, v2: 22 },
			{ name: "Nov", v1: 45, v2: 24 },
			{ name: "Dec", v1: 23, v2: 17 },
		];
	} finally {
		clearTimeout(timer);
	}
}

async function fetchUsage(headers = {}) {
	const API_BASE = process.env.NEXT_PUBLIC_API_URL || process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
	const controller = new AbortController();
	const timer = setTimeout(() => controller.abort(), 2500);
	try {
		const res = await fetch(`${API_BASE}/billing/usage`, { ...cacheOptions, headers, signal: controller.signal });
		if (!res.ok) throw new Error(`usage ${res.status}`);
		const json = await res.json();
		const used = Number(json.receiptsUsed ?? 0);
		const quota = Math.max(1, Number(json.receiptsQuota ?? 0));
		const pct = Math.min(100, Math.max(0, Math.round((used / quota) * 100)));
		return pct;
	} catch {
		return 80; // safe demo fallback
	} finally {
		clearTimeout(timer);
	}
}

async function fetchSubscriptions(headers = {}) {
	const API_BASE = process.env.NEXT_PUBLIC_API_URL || process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
	const controller = new AbortController();
	const timer = setTimeout(() => controller.abort(), 2500);
	try {
		const res = await fetch(`${API_BASE}/billing/subscriptions`, {
			...cacheOptions,
			headers,
			signal: controller.signal,
		});
		if (!res.ok) throw new Error(`subs ${res.status}`);
		const rows = await res.json();
		const fmt = new Intl.NumberFormat(undefined, { style: "currency", currency: rows?.[0]?.currency ?? "USD" });
		return (Array.isArray(rows) ? rows : []).slice(0, 5).map((s, idx) => ({
			id: String(s.id ?? `sub-${idx}`),
			title: String(s.name ?? s.provider ?? "Subscription"),
			icon: String(s.icon ?? s.logoUrl ?? "/assets/company-avatar-1.png"),
			costs: typeof s.amount === "number" ? fmt.format(s.amount / 100) : String(s.costs ?? "$0"),
			billingCycle: String(s.interval ?? s.billingCycle ?? "month"),
			status: String(s.status ?? "paid"),
		}));
	} catch {
		// Fallback to previous demo subscriptions
		return [
			{
				id: "supabase",
				title: "Supabase",
				icon: "/assets/company-avatar-5.png",
				costs: "$599",
				billingCycle: "year",
				status: "paid",
			},
			{
				id: "vercel",
				title: "Vercel",
				icon: "/assets/company-avatar-4.png",
				costs: "$20",
				billingCycle: "month",
				status: "expiring",
			},
			{
				id: "auth0",
				title: "Auth0",
				icon: "/assets/company-avatar-3.png",
				costs: "$20-80",
				billingCycle: "month",
				status: "canceled",
			},
			{
				id: "google_cloud",
				title: "Google Cloud",
				icon: "/assets/company-avatar-2.png",
				costs: "$100-200",
				billingCycle: "month",
				status: "paid",
			},
			{
				id: "stripe",
				title: "Stripe",
				icon: "/assets/company-avatar-1.png",
				costs: "$70",
				billingCycle: "month",
				status: "paid",
			},
		];
	} finally {
		clearTimeout(timer);
	}
}

export default async function Page() {
	// Server prefetch only public-ish panels; auth-required panels will fetch on the client via Clerk hooks
	const [summary, appUsage, usagePct, subscriptionsData] = await Promise.all([
		fetchSummary(),
		fetchAppUsage(),
		fetchUsage(),
		fetchSubscriptions(),
	]);
	const processedDiff = summary.processedPrev24h
		? Math.round(((summary.processed24h - summary.processedPrev24h) / Math.max(1, summary.processedPrev24h)) * 100)
		: 0;
	const processedTrend = processedDiff >= 0 ? "up" : "down";
	const accuracyInt = Number.isFinite(summary.avgAccuracy7d) ? Math.round(summary.avgAccuracy7d) : Number.NaN;
	const accuracyDiff =
		Number.isFinite(summary.avgAccuracy7d) && Number.isFinite(summary.avgAccuracyPrev7d)
			? Math.round(((summary.avgAccuracy7d - summary.avgAccuracyPrev7d) / Math.max(1, summary.avgAccuracyPrev7d)) * 100)
			: 0;
	const accuracyTrend = accuracyDiff >= 0 ? "up" : "down";
	const openAudits = summary.openAudits;
	return (
		<Box
			sx={{
				maxWidth: "var(--Content-maxWidth)",
				m: "var(--Content-margin)",
				p: "var(--Content-padding)",
				width: "var(--Content-width)",
			}}
		>
			<Stack spacing={4}>
				<TrialBanner />
				<DunningEntrypoint />
				<CheckoutReturnNotifier />
				<Stack direction={{ xs: "column", sm: "row" }} spacing={3} sx={{ alignItems: "center" }}>
					<Box sx={{ flex: "1 1 auto", display: "flex", gap: 1, alignItems: "center" }}>
						<Typography variant="h4">Overview</Typography>
						<PlanBadge />
					</Box>
					<div>
						<Button startIcon={<PlusIcon />} variant="contained">
							Dashboard
						</Button>
					</div>
				</Stack>
				<Grid container spacing={4}>
					<Grid
						size={{
							md: 4,
							xs: 12,
						}}
					>
						<Summary
							amount={summary.processed24h}
							diff={Math.abs(processedDiff)}
							icon={ListChecksIcon}
							title="Processed (24h)"
							trend={processedTrend}
						/>
					</Grid>
					<Grid
						size={{
							md: 4,
							xs: 12,
						}}
					>
						<Summary
							amount={Number.isFinite(accuracyInt) ? accuracyInt : 0}
							diff={Math.abs(accuracyDiff)}
							icon={UsersIcon}
							title="Avg accuracy (7d)"
							trend={accuracyTrend}
						/>
					</Grid>
					<Grid
						size={{
							md: 4,
							xs: 12,
						}}
					>
						<Summary
							amount={openAudits}
							diff={0}
							icon={WarningIcon}
							title="Open audits"
							trend={openAudits > 0 ? "up" : "down"}
						/>
					</Grid>
					<Grid
						size={{
							md: 8,
							xs: 12,
						}}
					>
						<AppUsage data={appUsage} />
					</Grid>
					<Grid size={{ md: 4, xs: 12 }}>
						<Subscriptions subscriptions={subscriptionsData} />
					</Grid>
					<Grid size={{ md: 4, xs: 12 }}>
						<AppChatClient limit={5} />
					</Grid>
					<Grid size={{ md: 4, xs: 12 }}>
						<EventsClient limit={4} />
					</Grid>
					<Grid size={{ md: 4, xs: 12 }}>
						<AppLimits usage={usagePct} />
					</Grid>
					<Grid
						size={{
							md: 4,
							xs: 12,
						}}
					>
						<HelperWidget
							action={
								<Button color="secondary" endIcon={<ArrowRightIcon />} size="small">
									Search jobs
								</Button>
							}
							description="Search for jobs that match your skills and apply to them directly."
							icon={BriefcaseIcon}
							label="Jobs"
							title="Find your dream job"
						/>
					</Grid>
					<Grid
						size={{
							md: 4,
							xs: 12,
						}}
					>
						<HelperWidget
							action={
								<Button color="secondary" endIcon={<ArrowRightIcon />} size="small">
									Help center
								</Button>
							}
							description="Find answers to your questions and get in touch with our team."
							icon={InfoIcon}
							label="Help center"
							title="Need help figuring things out?"
						/>
					</Grid>
					<Grid
						size={{
							md: 4,
							xs: 12,
						}}
					>
						<HelperWidget
							action={
								<Button color="secondary" endIcon={<ArrowRightIcon />} size="small">
									Documentation
								</Button>
							}
							description="Learn how to get started with our product and make the most of it."
							icon={FileCodeIcon}
							label="Documentation"
							title="Explore documentation"
						/>
					</Grid>
				</Grid>
			</Stack>
		</Box>
	);
}
