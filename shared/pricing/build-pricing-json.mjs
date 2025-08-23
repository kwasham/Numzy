#!/usr/bin/env node
// Generates a backend-consumable JSON snapshot of pricing catalog.
// Usage: node build-pricing-json.mjs > pricing-snapshot.json
import { PRICING_CATALOG, PRICING_ORDER } from "./catalog.js";

const snapshot = {
  generatedAt: new Date().toISOString(),
  order: PRICING_ORDER,
  plans: Object.values(PRICING_CATALOG).map((p) => ({
    id: p.id,
    monthly: p.monthly,
    discount: p.discount,
    description: p.description,
    quota: p.quota,
    features: p.features,
    recommended: p.recommended,
  })),
};

process.stdout.write(JSON.stringify(snapshot, null, 2));
