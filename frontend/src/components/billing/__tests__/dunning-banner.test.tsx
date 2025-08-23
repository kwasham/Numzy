import "@testing-library/jest-dom";

import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import { DunningBanner } from "../dunning-banner";

// Mock Clerk useAuth
jest.mock("@clerk/nextjs", () => ({
	useAuth: () => ({ getToken: async () => "tok_test" }),
}));

const originalFetch: typeof fetch | undefined = globalThis.fetch;

function mockStatus(payment_state: string | null) {
	const mockImpl: typeof fetch = (async () => ({
		ok: true,
		json: async () => ({ payment_state }),
	})) as unknown as typeof fetch;
	// @ts-expect-error override for test
	globalThis.fetch = mockImpl;
}

describe("DunningBanner", () => {
	beforeEach(() => {
		// restore original
		// @ts-expect-error restore
		globalThis.fetch = originalFetch;
	});

	it("renders nothing when ok", async () => {
		mockStatus("ok");
		render(<DunningBanner onFix={jest.fn()} />);
		await waitFor(() => {
			expect(screen.queryByText(/Action required/i)).not.toBeInTheDocument();
			expect(screen.queryByText(/Payment issue/i)).not.toBeInTheDocument();
		});
	});

	it("shows requires_action banner", async () => {
		mockStatus("requires_action");
		const onFix = jest.fn();
		render(<DunningBanner onFix={onFix} />);
		await screen.findByText(/Action required/i);
		const btn = screen.getByRole("button", { name: /Complete payment/i });
		fireEvent.click(btn);
		expect(onFix).toHaveBeenCalled();
	});

	it("shows past_due banner", async () => {
		mockStatus("past_due");
		const onFix = jest.fn();
		render(<DunningBanner onFix={onFix} />);
		await screen.findByText(/Payment issue/i);
		const btn = screen.getByRole("button", { name: /Fix payment/i });
		fireEvent.click(btn);
		expect(onFix).toHaveBeenCalled();
	});
});
