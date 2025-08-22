// Central pricing config & helpers
// Can later be replaced with dynamic fetch from backend

export const RAW_PRICING = {
	free: { monthly: 0, discount: 0 },
	personal: { monthly: 9.99, discount: 0.167 }, // 16.7% off annual
	pro: { monthly: 29, discount: 0.167 },
	business: { monthly: 99, discount: 0.167 },
};

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

export const PLAN_FEATURES = {
	free: ["25 monthly quota", "Retention: 30d", "Community support", "Basic analytics", "—"],
	personal: ["100 monthly quota", "Retention: 180d", "Community support", "Basic analytics", "—"],
	pro: ["500 monthly quota", "Retention: 365d", "Priority support", "Advanced analytics", "—"],
	business: ["5000 monthly quota", "Retention: Custom", "Priority support", "Advanced analytics", "SSO/SAML"],
};

// Feature descriptions for tooltips
export const FEATURE_DETAILS = {
	"Retention: 30d": "Your data is retained for 30 days.",
	"Retention: 180d": "Data retained for 6 months.",
	"Retention: 365d": "Data retained for 12 months.",
	"Retention: Custom": "Custom retention period negotiable on Business tier.",
	"Community support": "Best-effort community & forum assistance.",
	"Priority support": "Expedited responses with SLA targets.",
	"Basic analytics": "Core usage dashboards.",
	"Advanced analytics": "Drill-down & export capabilities.",
	SSO: "Single Sign-On via SAML/OIDC.",
	"SSO/SAML": "Enterprise SSO & SAML integration.",
};

export const PLAN_METADATA = {
	free: { name: "Free", description: "Free tier", recommended: false },
	personal: { name: "Personal", description: "Personal tier", recommended: false },
	pro: { name: "Pro", description: "Pro tier", recommended: true },
	business: { name: "Business", description: "Business tier", recommended: false },
};

export const PLAN_ORDER = ["free", "personal", "pro", "business"];

// Simple client-side currency conversion (display only, base USD)
export const BASE_CURRENCY = "USD";
export const CURRENCY_RATES = {
	USD: 1,
	EUR: 0.9,
};

export function convertPriceUSD(valueUSD, targetCurrency) {
	const rate = CURRENCY_RATES[targetCurrency] || 1;
	return roundCurrency(valueUSD * rate);
}
