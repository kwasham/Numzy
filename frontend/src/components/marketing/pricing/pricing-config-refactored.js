// Refactored pricing configuration aligned with updated pricing tiers

// Central pricing config & helpers
// These values reflect a four‑tier pricing structure with a new Enterprise plan.

export const RAW_PRICING = {
    free: { monthly: 0, discount: 0 },
    // Personal plan aimed at individuals and solo entrepreneurs. 9.99/month with ~16.7% annual discount.
    personal: { monthly: 9.99, discount: 0.167 },
    // Pro plan designed for small teams. The monthly price has been reduced from 29 to 19.99.
    pro: { monthly: 19.99, discount: 0.167 },
    // Business plan targeted at mid‑size organizations. Price lowered to 49.99 to align with market.
    business: { monthly: 49.99, discount: 0.167 },
    // Enterprise plan supports custom pricing; set monthly to 0 to signal that pricing is negotiated.
    enterprise: { monthly: 0, discount: 0 },
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

// Plan features have been expanded to clearly communicate quota, retention policy and key capabilities.
export const PLAN_FEATURES = {
    free: [
        "25 monthly quota",
        "Retention: 30d",
        "Community support",
        "Basic analytics",
        "—",
    ],
    personal: [
        "100 monthly quota",
        "Retention: 3y",
        "Community support",
        "Basic analytics",
        "PDF/CSV export",
    ],
    pro: [
        "500 monthly quota per user",
        "Retention: 7y",
        "Priority support",
        "Advanced analytics",
        "Integrations",
    ],
    business: [
        "Unlimited monthly quota",
        "Retention: 7y+",
        "Priority support",
        "Advanced analytics",
        "SSO/SAML & API",
    ],
    enterprise: [
        "Unlimited quota",
        "Retention: Custom",
        "Dedicated support",
        "Custom AI & on‑prem options",
        "SSO/SAML & API",
    ],
};

// Detailed descriptions for each feature; these strings appear in tooltips.
export const FEATURE_DETAILS = {
    "Retention: 30d": "Your data is retained for 30 days.",
    "Retention: 3y": "Data retained for 3 years, matching IRS general record‑keeping guidance.",
    "Retention: 7y": "Data retained for 7 years, suitable for standard business document retention.",
    "Retention: 7y+": "Data retained for 7 years or longer as needed.",
    "Retention: Custom": "Retention period negotiable for Enterprise customers.",
    "Community support": "Best‑effort community & forum assistance.",
    "Priority support": "Expedited responses with SLA targets.",
    "Dedicated support": "Dedicated account manager and priority assistance.",
    "Basic analytics": "Core usage dashboards.",
    "Advanced analytics": "Drill‑down reports, exports and trend analysis.",
    "PDF/CSV export": "Export your data in PDF or CSV formats for tax preparation.",
    Integrations: "Integrate with accounting software, Slack/Teams and other tools.",
    "SSO/SAML & API": "Enterprise Single Sign‑On and public API access.",
    "Custom AI & on‑prem options": "Customize models and deploy on your own infrastructure.",
};

export const PLAN_METADATA = {
    free: {
        name: "Free",
        description: "Starter plan for testing and exploration",
        recommended: false,
    },
    personal: {
        name: "Personal",
        description: "Ideal for individuals and freelancers",
        recommended: false,
    },
    pro: {
        name: "Pro",
        description: "For small teams and growing businesses",
        recommended: true,
    },
    business: {
        name: "Business",
        description: "Designed for mid‑size companies needing scalability and integration",
        recommended: false,
    },
    enterprise: {
        name: "Enterprise",
        description: "Custom solutions for large enterprises requiring compliance and flexibility",
        recommended: false,
    },
};

export const PLAN_ORDER = ["free", "personal", "pro", "business", "enterprise"];

export const BASE_CURRENCY = "USD";
export const CURRENCY_RATES = {
    USD: 1,
    EUR: 0.9,
};

export function convertPriceUSD(valueUSD, targetCurrency) {
    const rate = CURRENCY_RATES[targetCurrency] || 1;
    return roundCurrency(valueUSD * rate);
}