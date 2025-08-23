import { PRICING_CATALOG, PRICING_ORDER } from "@shared/pricing/catalog";

import { PLAN_FEATURES, PLAN_METADATA, PLAN_ORDER, PLAN_QUOTAS, RAW_PRICING } from "../pricing-config";

describe("pricing-config mapping", () => {
	it("mirrors order", () => {
		expect(PLAN_ORDER).toEqual(PRICING_ORDER);
	});
	it("mirrors raw pricing monthly & discount", () => {
		for (const id of PRICING_ORDER) {
			const src = PRICING_CATALOG[id];
			expect(RAW_PRICING[id]).toMatchObject({ monthly: src.monthly, discount: src.discount });
		}
	});
	it("mirrors feature arrays", () => {
		for (const id of PRICING_ORDER) {
			expect(PLAN_FEATURES[id]).toEqual(PRICING_CATALOG[id].features);
		}
	});
	it("mirrors quotas", () => {
		for (const id of PRICING_ORDER) {
			expect(PLAN_QUOTAS[id]).toEqual(PRICING_CATALOG[id].quota);
		}
	});
	it("metadata names/descriptions sync", () => {
		for (const id of PRICING_ORDER) {
			expect(PLAN_METADATA[id].description).toBe(PRICING_CATALOG[id].description);
		}
	});
});
