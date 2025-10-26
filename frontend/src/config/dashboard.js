import { paths } from "@/paths";

export const dashboardConfig = {
	layout: "vertical",
	navColor: "glass",
	navItems: [
		{
			key: "dashboards",
			title: "Dashboard",
			items: [
				{ key: "overview", title: "Overview", href: paths.dashboard.overview, icon: "house" },
				{ key: "receipts", title: "Receipts", href: paths.dashboard.receipts, icon: "upload" },
			],
		},
	],
};
