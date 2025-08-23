import "@testing-library/jest-dom";

import {
	discountPercent,
	generatePlanFeatures,
	PLAN_FEATURES,
	PLAN_QUOTAS,
	planPrice,
	priceMeta,
	RAW_PRICING,
} from "../pricing-config";

describe("pricing calculations", () => {
	it("has expected raw pricing entries for known plans", () => {
		expect(RAW_PRICING.free.monthly).toBe(0);
		expect(RAW_PRICING.pro.monthly).toBeGreaterThan(0);
		expect(RAW_PRICING.pro.discount).toBeGreaterThan(0);
	});

	it("computes annual total & equivalent monthly with discount (pro)", () => {
		const meta = priceMeta("pro");
		// Monthly list price
		expect(meta.monthly).toBeCloseTo(19.99, 2);
		// Annual should apply 16.7% discount (rounded 17%). Expect ~199.82
		expect(meta.annual).toBeCloseTo(199.82, 2);
		// Equivalent monthly from annual ~16.65
		expect(meta.annualMonthly).toBeCloseTo(16.65, 2);
		expect(meta.discountPercent).toBe(17); // rounded from 16.7%
	});

	it("planPrice respects yearly flag", () => {
		const monthly = planPrice("personal");
		const annual = planPrice("personal", { yearly: true });
		// Annual should be roughly monthly * 12 * (1 - discount)
		const raw = RAW_PRICING.personal;
		const expectedAnnual = +(raw.monthly * 12 * (1 - raw.discount)).toFixed(2);
		expect(monthly).toBeCloseTo(raw.monthly, 2);
		expect(annual).toBeCloseTo(expectedAnnual, 2);
	});

	it("discountPercent rounds correctly", () => {
		expect(discountPercent("pro")).toBe(17);
		expect(discountPercent("free")).toBe(0);
	});

	it("generatePlanFeatures preserves or rewrites first line appropriately", () => {
		// Pro plan: dynamic formatting should match original first feature (idempotent replacement)
		const proGenerated = generatePlanFeatures("pro");
		expect(proGenerated[0]).toMatch(/Process up to 500 .*receipts/);
		// Business: unlimited => Unlimited receipts / month
		const businessGenerated = generatePlanFeatures("business");
		expect(businessGenerated[0]).toBe("Unlimited receipts / month");
		// Enterprise: unlimited + custom => Unlimited receipts (custom SLA)
		const entGenerated = generatePlanFeatures("enterprise");
		expect(entGenerated[0]).toBe("Unlimited receipts (custom SLA)");
	});

	it("PLAN_FEATURES & PLAN_QUOTAS stay in sync for first feature substitution", () => {
		for (const id of Object.keys(PLAN_FEATURES)) {
			const generated = generatePlanFeatures(id);
			const hasQuota = !!PLAN_QUOTAS[id];
			if (hasQuota && PLAN_FEATURES[id].length > 0) {
				// Ensure generated array keeps length & rest of features stable
				expect(generated.length).toBe(PLAN_FEATURES[id].length);
				expect(generated.slice(1)).toEqual(PLAN_FEATURES[id].slice(1));
			}
		}
	});
});
