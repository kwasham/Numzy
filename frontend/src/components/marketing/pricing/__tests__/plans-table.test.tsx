import "@testing-library/jest-dom";

import { fireEvent, render, screen } from "@testing-library/react";

import { PlansTable } from "../plans-table";

// Mock pricing-config to provide deterministic data
jest.mock("../pricing-config", () => ({
	PLAN_FEATURES: {
		free: ["A"],
		personal: ["A", "B"],
	},
	RAW_PRICING: {
		free: { monthly: 0, discount: 0 },
		personal: { monthly: 9.99, discount: 0 },
	},
	generatePlanFeatures: (id: string) => {
		const map: Record<string, string[]> = { free: ["A"], personal: ["A", "B"] };
		return map[id] || [];
	},
	PLAN_METADATA: {
		free: { name: "Free", description: "Free plan", recommended: false },
		personal: { name: "Personal", description: "Personal plan", recommended: false },
	},
	FEATURE_DETAILS: { A: "Feature A", B: "Feature B" },
	PLAN_ORDER: ["free", "personal"],
	planPrice: (id: string) => (id === "free" ? 0 : 9.99),
	priceMeta: (id: string) => ({ monthly: id === "free" ? 0 : 9.99, annualMonthly: 0, discountPercent: 0 }),
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

	it("renders both plans", () => {
		render(<PlansTable />);
		expect(screen.getByText("Free")).toBeInTheDocument();
		expect(screen.getByText("Personal")).toBeInTheDocument();
	});

	it("persists selection to localStorage", () => {
		render(<PlansTable />);
		const selectBtns = screen.getAllByRole("button", { name: /select/i });
		fireEvent.click(selectBtns[0]);
		expect(localStorage.getItem("pricing:selectedPlan")).toBe("free");
	});
});
