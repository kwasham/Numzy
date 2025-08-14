import * as React from "react";

import { appConfig } from "@/config/app";
import { Faqs } from "@/components/marketing/home/faqs";
import { Features } from "@/components/marketing/home/features";
import { Hero } from "@/components/marketing/home/hero";
import { Included } from "@/components/marketing/home/included";
import { Productivity } from "@/components/marketing/home/productivity";
import { StartBuilding } from "@/components/marketing/home/start-building";
import { Testimonails } from "@/components/marketing/home/testimonials";

export const metadata = { title: appConfig.name, description: appConfig.description };

export default function Page() {
	return (
		<div>
			<Hero />
			<Productivity />
			<Included />
			<Features />
			<Testimonails />
			<Faqs />
			<StartBuilding />
		</div>
	);
}
