// Canonical pricing catalog (single source of truth)
// NOTE: Frontend pricing-config.js derives its exports from this file.
// Fields:
// - id: plan identifier
// - monthly: base monthly USD price (0 for custom/negotiated)
// - discount: annual discount (0..1) applied to 12 * monthly when billed yearly
// - description: marketing description
// - features: base feature strings (first line will be replaced dynamically if quota present)
// - quota: { limit, perUser, unlimited, custom }
// - recommended: boolean to highlight plan

export const PRICING_CATALOG = {
  free: {
    id: "free",
    monthly: 0,
    discount: 0,
    description: "Starter plan for testing and exploration",
    features: [
      "Process up to 25 receipts / month",
      "Data retention: 30 days",
      "Community support",
      "Basic analytics",
    ],
    quota: { limit: 25 },
    recommended: false,
  },
  personal: {
    id: "personal",
    monthly: 9.99,
    discount: 0.167,
    description: "Ideal for individuals and freelancers",
    features: [
      "Process up to 25 receipts / month",
      "Data retention: 3 years",
      "Community support",
      "Basic analytics",
      "PDF/CSV export",
    ],
    quota: { limit: 25 },
    recommended: false,
  },
  pro: {
    id: "pro",
    monthly: 19.99,
    discount: 0.167,
    description: "For small teams and growing businesses",
    features: [
      "Process up to 500 receipts / user / month",
      "Data retention: 7 years",
      "Priority support",
      "Advanced analytics & reporting",
      "Spending summary dashboard",
      "PDF/CSV export",
      "Integrations (Slack, Accounting)",
    ],
    quota: { limit: 500, perUser: true },
    recommended: true,
  },
  business: {
    id: "business",
    monthly: 49.99,
    discount: 0.167,
    description:
      "Designed for mid‑size companies needing scalability and integration",
    features: [
      "Unlimited receipts / month",
      "Data retention: 7+ years",
      "Priority support",
      "Advanced analytics & reporting",
      "SSO / SAML + API access",
    ],
    quota: { unlimited: true },
    recommended: false,
  },
  enterprise: {
    id: "enterprise",
    monthly: 0, // custom pricing
    discount: 0,
    description:
      "Custom solutions for large enterprises requiring compliance and flexibility",
    features: [
      "Unlimited receipts (custom SLA)",
      "Data retention: Custom",
      "Dedicated support",
      "Custom AI & on‑prem options",
      "SSO / SAML + API access",
    ],
    quota: { unlimited: true, custom: true },
    recommended: false,
  },
};

export const PRICING_ORDER = [
  "free",
  "personal",
  "pro",
  "business",
  "enterprise",
];
