import Divider from "@mui/material/Divider";

import { appConfig } from "@/config/app";
import { Faqs } from "@/components/marketing/pricing/faqs";
import { PlansTable } from "@/components/marketing/pricing/plans-table";

// Optional: bring in billing buttons for quick wiring
// import { BillingButtons } from "@/components/billing/billing-buttons";

export const metadata = { title: `Pricing | ${appConfig.name}` };

export default function Page() {
	return (
		<div>
			<PlansTable />
			<Divider />
			<Faqs />
			{/**
			<div style={{ padding: 24 }}>
				<BillingButtons />
			</div>
			**/}
		</div>
	);
}
