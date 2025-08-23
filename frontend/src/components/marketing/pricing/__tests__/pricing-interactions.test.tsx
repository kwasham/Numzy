import "@testing-library/jest-dom";

import { fireEvent, render, screen } from "@testing-library/react";

import { Plan } from "../plan";
import { PlansTable } from "../plans-table";

// Stub IntersectionObserver to immediately report intersection
class IOStub {
	callback: IntersectionObserverCallback;
	constructor(cb: IntersectionObserverCallback) {
		this.callback = cb;
	}
	observe(target: Element) {
		// simulate async visibility
		setTimeout(() => {
			this.callback(
				[{ isIntersecting: true, target } as unknown as IntersectionObserverEntry],
				this as unknown as IntersectionObserver
			);
		}, 0);
	}
	unobserve() {}
	disconnect() {}
}
// @ts-expect-error test shim
globalThis.IntersectionObserver = IOStub;

describe("Pricing interactions", () => {
	beforeEach(() => {
		jest.useFakeTimers();
	});
	afterEach(() => {
		jest.runOnlyPendingTimers();
		jest.useRealTimers();
	});

	it("keyboard Enter selects a plan", () => {
		const onSelect = jest.fn();
		render(
			<Plan
				action={undefined}
				currency="USD"
				description="Desc"
				id="pro"
				features={[]}
				name="Pro"
				price={19.99}
				period="/month"
				monthlyReference={undefined}
				discountPercent={undefined}
				recommended={false}
				selected={false}
				onSelect={onSelect}
			/>
		);
		const card = screen.getByRole("group", { name: /pro plan/i });
		fireEvent.keyDown(card, { key: "Enter" });
		expect(onSelect).toHaveBeenCalledWith("pro");
	});

	it("yearly toggle updates price & shows discount info", () => {
		render(<PlansTable />);
		// Pro monthly price visible
		expect(screen.getByText(/\$19\.99/)).toBeInTheDocument();
		const toggle = screen.getByRole("checkbox", { name: /toggle annual billing/i });
		fireEvent.click(toggle);
		// annual price appears (approx $199.xx) - allow variance by using a function matcher
		expect(screen.getByText((content) => content.startsWith("$199") && content.length <= 8)).toBeInTheDocument();
		// at least one monthly reference with save visible
		const refs = screen.getAllByText((c) => c.includes("/ month") && /Save 17%/.test(c));
		expect(refs.length).toBeGreaterThan(0);
	});

	it("dispatches select event", () => {
		const selectListener = jest.fn();
		globalThis.addEventListener("pricing:select", selectListener);
		render(<PlansTable />);
		// click Select on Free plan
		fireEvent.click(screen.getAllByRole("button", { name: /select/i })[0]);
		expect(selectListener).toHaveBeenCalled();
	});

	it("debounces impression events (fires after timeout)", () => {
		const impressionListener = jest.fn();
		globalThis.addEventListener("pricing:impression", impressionListener);
		render(<PlansTable />);
		// Initially no events before timers run
		expect(impressionListener).not.toHaveBeenCalled();
		jest.advanceTimersByTime(61);
		expect(impressionListener).toHaveBeenCalled();
	});
});
