import "@testing-library/jest-dom";

import { fireEvent, render, screen } from "@testing-library/react";

import { PlansTable } from "../plans-table";

// Mock pricing-config to provide deterministic data
jest.mock("../pricing-config", () => ({
	PLAN_FEATURES: {
		personal: ["A", "B"],
	},
	RAW_PRICING: {
		personal: { monthly: 9.99, discount: 0 },
	},
	generatePlanFeatures: (id: string) => {
		const map: Record<string, string[]> = { personal: ["A", "B"] };
		return map[id] || [];
	},
	PLAN_METADATA: {
		personal: { name: "Personal", description: "Personal plan", recommended: false },
	},
	FEATURE_DETAILS: { A: "Feature A", B: "Feature B" },
	PLAN_ORDER: ["free", "personal"], // free exists but should be filtered out by component
	planPrice: () => 9.99,
	priceMeta: () => ({ monthly: 9.99, annualMonthly: 0, discountPercent: 0 }),
}));

// Silence intersection observer
class IOStub {
	observe() {}
	unobserve() {}
	disconnect() {}
}
// @ts-expect-error test shim
globalThis.IntersectionObserver = IOStub;

describe("PlansTable", () => {
	beforeEach(() => {
		localStorage.clear();
	});

	it("renders only paid plan(s) (free hidden)", () => {
		render(<PlansTable />);
		expect(screen.queryByText("Free")).not.toBeInTheDocument();
		expect(screen.getByText("Personal")).toBeInTheDocument();
	});

	it("persists selection of available plan to localStorage", () => {
		render(<PlansTable />);
		const selectBtns = screen.getAllByRole("button", { name: /select/i });
		fireEvent.click(selectBtns[0]);
		expect(localStorage.getItem("pricing:selectedPlan")).toBe("personal");
	});
});
