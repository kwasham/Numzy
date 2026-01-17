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
import { SPENDING_TREND_SEED } from "@/data/spending-trend-seed";
import { DunningEntrypoint } from "@/components/billing/dunning-entrypoint";
import { PlanBadge } from "@/components/billing/plan-badge";
import { TrialBanner } from "@/components/billing/trial-banner";
import { AppChatClient } from "@/components/dashboard/overview/app-chat-client";
import { AppLimits } from "@/components/dashboard/overview/app-limits";
import { AppUsage } from "@/components/dashboard/overview/app-usage";
import { BudgetProgressCard } from "@/components/dashboard/overview/budget-progress-card";
import { CATEGORY_COLORS, CategoryPieCard } from "@/components/dashboard/overview/category-pie-card";
import { CheckoutReturnNotifier } from "@/components/dashboard/overview/checkout-return-notifier";
import { EventsClient } from "@/components/dashboard/overview/events-client";
import { HelperWidget } from "@/components/dashboard/overview/helper-widget";
import { MonthlySpendingCard } from "@/components/dashboard/overview/monthly-spending-card";
import { SpendingTrendChart } from "@/components/dashboard/overview/spending-trend-chart";
import { Subscriptions } from "@/components/dashboard/overview/subscriptions";
import { Summary } from "@/components/dashboard/overview/summary";
import { TransactionsList } from "@/components/dashboard/overview/transactions-list";

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

async function fetchCategorySpend(headers = {}) {
	// Try multiple candidates to work both locally and in Docker (api service hostname)
	const candidates = [
		process.env.NEXT_PUBLIC_API_URL,
		process.env.NEXT_PUBLIC_API_BASE_URL,
		"http://localhost:8000",
		"http://api:8000",
	].filter(Boolean);
	// Category aggregation can run a heavier SQL; give it a bit more headroom.
	for (const base of candidates) {
		const controller = new AbortController();
		const timer = setTimeout(() => controller.abort(), 5000);
		try {
			const res = await fetch(`${base}/metrics/spend/categories?limit=6&window_days=3650`, {
				...cacheOptions,
				headers,
				signal: controller.signal,
			});
			if (!res.ok) throw new Error(`category ${res.status}`);
			const json = await res.json();
			if (!json || !Array.isArray(json.items)) {
				continue;
			}
			const items = json.items
				.map((item) => ({
					name: typeof item.name === "string" && item.name.trim().length > 0 ? item.name.trim() : "Uncategorized",
					amount: Number(item.amount ?? item.total ?? 0) || 0,
					count: Number.isFinite(Number(item.count)) ? Number(item.count) : undefined,
				}))
				.filter((item) => Number.isFinite(item.amount) && item.amount > 0);
			const total = Number(json.total ?? 0) || items.reduce((acc, item) => acc + item.amount, 0);
			return { total, items };
		} catch {
			// try next candidate base
		} finally {
			clearTimeout(timer);
		}
	}
	return null;
}

export default async function Page() {
	// Server prefetch only public-ish panels; auth-required panels will fetch on the client via Clerk hooks
	const [summary, appUsage, usagePct, subscriptionsData, categorySpend] = await Promise.all([
		fetchSummary(),
		fetchAppUsage(),
		fetchUsage(),
		fetchSubscriptions(),
		fetchCategorySpend(),
	]);
	const monthlyBudget = 5000;
	const subscriptionExpense = subscriptionsData.reduce((acc, sub) => {
		if (typeof sub.costs !== "string") return acc;
		const numeric = Number.parseFloat(sub.costs.replaceAll(/[^\d.-]/g, ""));
		return Number.isFinite(numeric) ? acc + Math.max(0, numeric) : acc;
	}, 0);
	const categoryFallback = [
		{ name: "Software subscriptions", value: 1800, color: CATEGORY_COLORS[0] },
		{ name: "Infrastructure", value: 1400, color: CATEGORY_COLORS[1] },
		{ name: "Operations", value: 900, color: CATEGORY_COLORS[2] },
	];
	const fallbackTotal = categoryFallback.reduce((acc, category) => acc + category.value, 0);
	let categoryBreakdown = categoryFallback;
	let monthlyExpense = fallbackTotal;
	if (categorySpend && categorySpend.items.length > 0) {
		categoryBreakdown = categorySpend.items.map((item, index) => ({
			name: item.name,
			value: Math.round(item.amount * 100) / 100,
			color: CATEGORY_COLORS[index % CATEGORY_COLORS.length],
		}));
		monthlyExpense = categoryBreakdown.reduce((acc, category) => acc + category.value, 0);
	} else if (subscriptionExpense > 0) {
		const categoryWeights = [
			{ name: "Software subscriptions", weight: 0.45 },
			{ name: "Infrastructure", weight: 0.35 },
			{ name: "Operations", weight: 0.2 },
		];
		categoryBreakdown = categoryWeights.map(({ name, weight }, index) => ({
			name,
			value: Math.round(subscriptionExpense * weight * 100) / 100,
			color: CATEGORY_COLORS[index % CATEGORY_COLORS.length],
		}));
		monthlyExpense = subscriptionExpense;
	}
	const budgetProgressData = categoryBreakdown.map((category, index) => {
		const fallbackBudget = monthlyBudget / Math.max(1, categoryBreakdown.length);
		const ratio = monthlyExpense > 0 ? category.value / monthlyExpense : 1 / Math.max(1, categoryBreakdown.length);
		const projectedBudget = Math.round(monthlyBudget * ratio * 100) / 100;
		return {
			name: category.name,
			spent: category.value,
			budget: projectedBudget > 0 ? projectedBudget : fallbackBudget,
			color: category.color ?? CATEGORY_COLORS[index % CATEGORY_COLORS.length],
		};
	});
	const today = new Date();
	const spendingTrendData = SPENDING_TREND_SEED.map(({ label, spent, budget }) => ({
		month: label,
		spent,
		budget,
	}));
	const transactionsSample =
		subscriptionsData.length > 0
			? subscriptionsData.slice(0, 5).map((subscription, index) => {
					const numeric =
						typeof subscription.costs === "string"
							? Number.parseFloat(subscription.costs.replaceAll(/[^\d.-]/g, ""))
							: Number(subscription.costs ?? 0);
					const day = new Date(today.getTime() - index * 86_400_000);
					return {
						id: String(subscription.id ?? index),
						date: day.toISOString().slice(0, 10),
						description: subscription.title ?? "Subscription charge",
						category: subscription.billingCycle ? `${subscription.billingCycle} billing` : "Subscription",
						amount: -Math.abs(Number.isFinite(numeric) ? numeric : 0),
						currency: "USD",
					};
				})
			: undefined;
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
					<Grid size={{ xs: 12 }}>
						<Grid container spacing={4}>
							<Grid size={{ xs: 12, md: 4 }}>
								<MonthlySpendingCard budget={monthlyBudget} totalExpense={monthlyExpense} />
							</Grid>
							<Grid size={{ xs: 12, md: 4 }}>
								{/* Only pass categories to the card when we have real backend data; otherwise let it self-fetch */}
								<CategoryPieCard
									categories={categorySpend && categorySpend.items.length > 0 ? categoryBreakdown : undefined}
									totalLabel="Monthly total"
								/>
							</Grid>
							<Grid size={{ xs: 12, md: 4 }}>
								<BudgetProgressCard categories={budgetProgressData} />
							</Grid>
						</Grid>
					</Grid>
					<Grid size={{ xs: 12 }}>
						<Grid container spacing={4}>
							<Grid size={{ xs: 12, md: 4 }}>
								<Summary
									amount={summary.processed24h}
									diff={Math.abs(processedDiff)}
									icon={ListChecksIcon}
									title="Processed (24h)"
									trend={processedTrend}
								/>
							</Grid>
							<Grid size={{ xs: 12, md: 4 }}>
								<Summary
									amount={Number.isFinite(accuracyInt) ? accuracyInt : 0}
									diff={Math.abs(accuracyDiff)}
									icon={UsersIcon}
									title="Avg accuracy (7d)"
									trend={accuracyTrend}
								/>
							</Grid>
							<Grid size={{ xs: 12, md: 4 }}>
								<Summary
									amount={openAudits}
									diff={0}
									icon={WarningIcon}
									title="Open audits"
									trend={openAudits > 0 ? "up" : "down"}
								/>
							</Grid>
						</Grid>
					</Grid>
					<Grid container spacing={4} size={{ xs: 12 }}>
						<Grid size={{ xs: 12, lg: 8 }}>
							<Stack spacing={4}>
								<SpendingTrendChart data={spendingTrendData} />
								<AppUsage data={appUsage} />
								<TransactionsList transactions={transactionsSample} />
							</Stack>
						</Grid>
						<Grid size={{ xs: 12, lg: 4 }}>
							<Stack spacing={4}>
								<Subscriptions subscriptions={subscriptionsData} />
								<AppLimits usage={usagePct} />
								<EventsClient limit={4} />
								<AppChatClient limit={5} />
							</Stack>
						</Grid>
					</Grid>
					<Grid container spacing={4} size={{ xs: 12 }}>
						<Grid size={{ xs: 12, md: 4 }}>
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
						<Grid size={{ xs: 12, md: 4 }}>
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
						<Grid size={{ xs: 12, md: 4 }}>
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
				</Grid>
			</Stack>
		</Box>
	);
}
