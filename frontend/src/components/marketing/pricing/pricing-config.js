// Pricing configuration now derives from shared catalog (single source of truth)
// Shared module path: ../../../../../shared/pricing/catalog.js (outside frontend package)
// Importing via relative path; Next.js transpiles it.
import { PRICING_CATALOG } from "../../../../../shared/pricing/catalog";

// Backwards compatible shape for existing helpers
export const RAW_PRICING = Object.fromEntries(
	Object.entries(PRICING_CATALOG).map(([id, v]) => [id, { monthly: v.monthly, discount: v.discount }])
);

export function annualTotal({ monthly, discount }) {
	const base = monthly * 12;
	const total = base * (1 - discount);
	return roundCurrency(total);
}

export function equivalentMonthlyFromAnnual({ monthly, discount }) {
	const total = annualTotal({ monthly, discount });
	return roundCurrency(total / 12);
}

export function planPrice(id, opts) {
	const yearly = opts?.yearly || false;
	const entry = RAW_PRICING[id];
	if (!entry) return 0;
	if (yearly) return annualTotal(entry);
	return entry.monthly;
}

export function discountPercent(id) {
	const entry = RAW_PRICING[id];
	if (!entry) return 0;
	return Math.round(entry.discount * 100);
}

export function priceMeta(id) {
	const entry = RAW_PRICING[id];
	if (!entry) return {};
	return {
		monthly: entry.monthly,
		annual: annualTotal(entry),
		annualMonthly: equivalentMonthlyFromAnnual(entry),
		discountPercent: discountPercent(id),
	};
}

function roundCurrency(v) {
	return Math.round((v + Number.EPSILON) * 100) / 100;
}

// Plan features have been expanded to clearly communicate quota, retention policy and key capabilities.
export const PLAN_FEATURES = Object.fromEntries(Object.entries(PRICING_CATALOG).map(([id, v]) => [id, v.features]));

// Quota definitions (single source of truth for first feature line formatting)
// This enables consistent pluralization & large number formatting without hardcoding
// strings directly in PLAN_FEATURES. We still keep the original first string in
// PLAN_FEATURES for backward compatibility & tests; generatePlanFeatures() will
// re-format it dynamically using these values so future changes only update this map.
// Fields:
// - limit: numeric upper bound
// - perUser: whether the quota is per user
// - unlimited: boolean for unlimited tiers
// - custom: indicates custom / negotiated terms (enterprise)
export const PLAN_QUOTAS = Object.fromEntries(Object.entries(PRICING_CATALOG).map(([id, v]) => [id, v.quota]));

// Format a numeric quantity with optional compact notation (e.g. 1,200 -> 1.2K)
function formatNumber(value) {
	if (value >= 1000) {
		// Use Intl with compact if supported; fallback to manual K/M formatting.
		try {
			return new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 }).format(value);
		} catch {
			if (value < 1_000_000) return (value / 1000).toFixed(value % 1000 === 0 ? 0 : 1) + "K";
			return (value / 1_000_000).toFixed(value % 1_000_000 === 0 ? 0 : 1) + "M";
		}
	}
	return value.toString();
}

// Public helper: format receipt quota with proper singular/plural & modifiers.
export function formatReceiptQuota({ limit, perUser, unlimited, custom }) {
	if (unlimited) {
		if (custom) return "Unlimited receipts (custom SLA)"; // enterprise wording
		return "Unlimited receipts / month"; // business wording
	}
	if (limit == null) return "—";
	const num = formatNumber(limit);
	const singular = limit === 1;
	// When compact notation yields e.g. "1K" we always use plural form.
	const unit = singular && !/[^0-9]/.test(num) ? "receipt" : "receipts";
	return `Process up to ${num} ${unit} ${perUser ? "/ user " : "/ "}month`;
}

// Generate full feature list for a plan, replacing first quota line with
// dynamically formatted version (keeping rest intact). Falls back gracefully
// if PLAN_FEATURES does not contain any features or quota map missing.
export function generatePlanFeatures(id) {
	const base = PLAN_FEATURES[id] || [];
	if (base.length === 0) return base;
	const quota = PLAN_QUOTAS[id];
	if (!quota) return base; // no dynamic override
	const formatted = formatReceiptQuota(quota);
	// Replace only if different to avoid altering feature delta logic unnecessarily.
	const updated = [formatted, ...base.slice(1)];
	return updated;
}

// Detailed descriptions for each feature; these strings appear in tooltips.
export const FEATURE_DETAILS = {
	"Process up to 25 receipts / month": "Monthly receipt processing capacity for the Free plan.",
	"Process up to 100 receipts / month": "Monthly receipt processing capacity for the Personal plan.",
	"Process up to 500 receipts / user / month": "Per-user monthly receipt volume for Pro teams.",
	"Unlimited receipts / month": "No fixed monthly receipt cap; fair use policy may apply.",
	"Unlimited receipts (custom SLA)": "Unlimited with contractual throughput & uptime guarantees.",
	"Data retention: 30 days": "Receipts stored for 30 days then purged automatically.",
	"Data retention: 3 years": "Retention aligns with common tax documentation requirements.",
	"Data retention: 7 years": "Extended retention for audit and compliance needs.",
	"Data retention: 7+ years": "Long‑term retention beyond 7 years as required.",
	"Data retention: Custom": "Tailored retention policy negotiated for your compliance needs.",
	"Community support": "Access to community forum & public knowledge base.",
	"Priority support": "Faster response times via email (SLA targets).",
	"Dedicated support": "Named account manager plus prioritized escalation paths.",
	"Basic analytics": "Essential usage and volume metrics dashboard.",
	"Advanced analytics & reporting": "Drill‑down filters, trends, exports & comparative insights.",
	"PDF/CSV export": "Download structured data for bookkeeping or analysis.",
	"Integrations (Slack, Accounting)": "Out‑of‑the‑box connectors to Slack and popular accounting tools.",
	"SSO / SAML + API access": "Single Sign‑On plus full REST API access for automation.",
	"Custom AI & on‑prem options": "Bring your own models or deploy on private infrastructure.",
};

export const PLAN_METADATA = Object.fromEntries(
	Object.entries(PRICING_CATALOG).map(([id, v]) => [
		id,
		{ name: capitalize(id), description: v.description, recommended: v.recommended },
	])
);

function capitalize(id) {
	return id.charAt(0).toUpperCase() + id.slice(1);
}

export const BASE_CURRENCY = "USD";
export const CURRENCY_RATES = {
	USD: 1,
	EUR: 0.9,
};

export function convertPriceUSD(valueUSD, targetCurrency) {
	const rate = CURRENCY_RATES[targetCurrency] || 1;
	return roundCurrency(valueUSD * rate);
}

export { PRICING_ORDER as PLAN_ORDER } from "../../../../../shared/pricing/catalog";
