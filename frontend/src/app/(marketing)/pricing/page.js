import * as React from "react";
import Divider from "@mui/material/Divider";

import { appConfig } from "@/config/app";
import { Faqs } from "@/components/marketing/pricing/faqs";
import { PlansTable } from "@/components/marketing/pricing/plans-table";

export const metadata = { title: `Pricing | ${appConfig.name}` };

export default function Page() {
	return (
		<div>
			<PlansTable />
			<Divider />
			<Faqs />
		</div>
	);
}
