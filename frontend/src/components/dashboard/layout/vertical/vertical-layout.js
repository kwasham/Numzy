"use client";

import * as React from "react";
import { useUser } from "@clerk/nextjs";
import Box from "@mui/material/Box";
import GlobalStyles from "@mui/material/GlobalStyles";

import { dashboardConfig } from "@/config/dashboard";
import { useSettings } from "@/components/core/settings/settings-context";

import { MainNav } from "./main-nav";
import { SideNav } from "./side-nav";

export function VerticalLayout({ children }) {
	const { settings } = useSettings();
	const { user, isLoaded } = useUser();

	const navColor = settings.dashboardNavColor ?? dashboardConfig.navColor;

	const userRoles = React.useMemo(() => {
		const pm = user?.publicMetadata;
		if (!pm) return [];
		if (Array.isArray(pm.roles)) return pm.roles;
		if (typeof pm.role === "string") return [pm.role];
		return [];
	}, [user]);

	const filteredNavItems = React.useMemo(() => {
		// Safe default: if user is not loaded yet, hide role-gated items
		const roles = isLoaded ? userRoles : [];

		const filterItems = (items = []) => {
			return items
				.filter((item) => {
					if (!item?.roles || item.roles.length === 0) return true;
					return roles.some((r) => item.roles.includes(r));
				})
				.map((item) => {
					if (item.items && Array.isArray(item.items)) {
						const next = filterItems(item.items);
						return { ...item, items: next };
					}
					return item;
				})
				.filter((item) => !(item.items && item.items.length === 0));
		};

		// navItems is an array of groups each with `items`
		return (dashboardConfig.navItems || [])
			.map((group) => ({ ...group, items: filterItems(group.items || []) }))
			.filter((group) => group.items && group.items.length > 0);
	}, [isLoaded, userRoles]);

	return (
		<React.Fragment>
			<GlobalStyles
				styles={{
					body: {
						"--MainNav-height": "56px",
						"--MainNav-zIndex": 1000,
						"--SideNav-width": "280px",
						"--SideNav-zIndex": 1100,
						"--MobileNav-width": "320px",
						"--MobileNav-zIndex": 1100,
					},
				}}
			/>
			<Box
				sx={{
					bgcolor: "var(--mui-palette-background-default)",
					display: "flex",
					flexDirection: "column",
					position: "relative",
					minHeight: "100%",
				}}
			>
				<SideNav color={navColor} items={filteredNavItems} />
				<Box sx={{ display: "flex", flex: "1 1 auto", flexDirection: "column", pl: { lg: "var(--SideNav-width)" } }}>
					<MainNav items={filteredNavItems} />
					<Box
						component="main"
						sx={{
							"--Content-margin": "0 auto",
							"--Content-maxWidth": "var(--maxWidth-xl)",
							"--Content-paddingX": "24px",
							"--Content-paddingY": { xs: "24px", lg: "64px" },
							"--Content-padding": "var(--Content-paddingY) var(--Content-paddingX)",
							"--Content-width": "100%",
							display: "flex",
							flex: "1 1 auto",
							flexDirection: "column",
						}}
					>
						{children}
					</Box>
				</Box>
			</Box>
		</React.Fragment>
	);
}
