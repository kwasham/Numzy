import { appConfig } from "@/config/app";
import { TestBillingPricing } from "@/components/marketing/pricing/test-billing/test-billing-pricing";

export const metadata = { title: `Test Billing | ${appConfig.name}` };

export default function Page() {
	return <TestBillingPricing />;
}
