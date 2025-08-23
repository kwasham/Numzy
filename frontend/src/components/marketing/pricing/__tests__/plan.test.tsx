import "@testing-library/jest-dom";

import { fireEvent, render, screen } from "@testing-library/react";

import { Plan } from "../plan";

// Minimal FEATURE_DETAILS mock (module import inside Plan references pricing-config)
jest.mock("../pricing-config", () => ({
	FEATURE_DETAILS: {},
}));

describe("Plan component", () => {
	const baseProps = {
		action: undefined,
		currency: "USD",
		description: "Test plan",
		id: "pro",
		features: ["Feature A"],
		name: "Pro",
		price: 19.99,
		period: "/month",
		monthlyReference: undefined,
		discountPercent: undefined,
		recommended: false,
		selected: false,
		onSelect: jest.fn(),
	};

	it("renders price and name", () => {
		render(<Plan {...baseProps} />);
		expect(screen.getByText("Pro")).toBeInTheDocument();
		expect(screen.getByText(/19\.99/)).toBeInTheDocument();
	});

	it("calls onSelect when Select clicked", () => {
		const onSelect = jest.fn();
		render(<Plan {...baseProps} onSelect={onSelect} />);
		fireEvent.click(screen.getByRole("button", { name: /select/i }));
		expect(onSelect).toHaveBeenCalledWith("pro");
	});

	it("shows Selected when already selected", () => {
		render(<Plan {...baseProps} selected />);
		expect(screen.getByRole("button", { name: /selected/i })).toBeDisabled();
	});
});
