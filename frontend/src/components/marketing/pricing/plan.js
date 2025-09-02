import * as React from "react";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import Chip from "@mui/material/Chip";
import Divider from "@mui/material/Divider";
import Stack from "@mui/material/Stack";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import { CheckIcon } from "@phosphor-icons/react/dist/ssr/Check";

import { FEATURE_DETAILS } from "./pricing-config";
import { ACCENT_COLOR_MAP } from "./pricing-theme";

/**
 * Unified Plan component (final version):
 * - Accent bar & recommended styling
 * - Selection highlight & keyboard accessibility
 * - Custom pricing label for enterprise tier
 * - Tooltip feature details
 * This is the single exported implementation; prior variants removed.
 */
export function Plan({
	action, // optional legacy prop; if supplied overrides internal button
	currency,
	description,
	id,
	features,
	name,
	price,
	period = "/month",
	monthlyReference,
	discountPercent,
	recommended = false,
	selected, // may be undefined; if so we manage internal state
	onSelect,
}) {
	// Internal fallback selection state so component gives user feedback even if uncontrolled
	const [internalSelected, setInternalSelected] = React.useState(false);
	const hasControlledSelected = typeof selected === "boolean";
	const effectiveSelected = hasControlledSelected ? selected : internalSelected;
	// Define base and recommended styles.  These leverage the MUI theme
	// palette so colors automatically adjust between light/dark modes.
	const baseStyles = {
		backgroundColor: (theme) => theme.palette.grey[900],
		borderRadius: 2,
		border: "1px solid",
		borderColor: "divider",
		boxShadow: 4,
		p: 3,
		transition: "transform 0.2s ease, box-shadow 0.2s ease",
		"&:hover": {
			boxShadow: 8,
			transform: "translateY(-2px)",
		},
	};

	const recommendedStyles = {
		...baseStyles,
		borderColor: "primary.main",
		transform: "scale(1.03)",
		zIndex: 1,
	};

	// Accent color map externalized (see pricing-theme.js)

	// Convert price to display string; enterprise uses custom pricing label.
	const priceDisplay =
		price === 0 && id === "enterprise"
			? "Custom pricing"
			: new Intl.NumberFormat("en-US", {
					style: "currency",
					currency,
					maximumFractionDigits: price === 0 ? 0 : 2,
				}).format(price);

	return (
		<Card
			data-pricing-card="true"
			data-plan={id}
			sx={{
				...(recommended ? recommendedStyles : baseStyles),
				// Provide a consistent width baseline so multi-row layouts align nicely.
				// width: { xs: 260, sm: 300, md: 320 },
				// mx: { xs: 0.5, md: 1 },
				// my: { xs: 0, md: 1 },
				// Removed selected highlight styling & pointer cursor per request.
			}}
			role="group"
			tabIndex={0}
			aria-label={`${name} plan${effectiveSelected ? " selected" : ""}`}
			onKeyDown={(e) => {
				if ((e.key === "Enter" || e.key === " ") && !effectiveSelected && id !== "business") {
					e.preventDefault();
					if (onSelect) {
						onSelect(id);
					} else {
						setInternalSelected(true);
					}
					globalThis?.dispatchEvent(
						new CustomEvent("pricing:select", { detail: { plan: id, yearly: period === "/year" } })
					);
				}
				if ((e.key === "Enter" || e.key === " ") && id === "business") {
					e.preventDefault();
					globalThis?.dispatchEvent(new CustomEvent("pricing:contact", { detail: { plan: id } }));
					globalThis.location.href = "mailto:sales@example.com?subject=Business%20Plan%20Inquiry";
				}
			}}
		>
			{/* Accent bar */}
			<Box
				sx={{
					height: 4,
					backgroundColor: ACCENT_COLOR_MAP[id] || "divider",
					borderTopLeftRadius: 8,
					borderTopRightRadius: 8,
					mb: 2,
				}}
			/>
			{/* Badges */}
			<Stack direction="row" spacing={1} sx={{ mb: 1 }}>
				{recommended && <Chip label="Recommended" color="primary" size="small" />}
				{/* Removed selected chip highlight per request */}
			</Stack>
			{/* Plan name and description */}
			<Stack spacing={1} sx={{ mb: 2 }}>
				<Typography variant="h5" component="h3">
					{name}
				</Typography>
				<Typography variant="subtitle1" color="text.secondary">
					{description}
				</Typography>
			</Stack>
			{/* Price section */}
			<Box sx={{ mb: 3 }}>
				<Typography variant="h3" component="span">
					{priceDisplay}
				</Typography>
				{price !== 0 && (
					<Typography component="span" variant="h6" sx={{ ml: 0.5 }}>
						{period}
					</Typography>
				)}
				{period === "/year" && monthlyReference != null && (
					<Typography variant="caption" color="text.secondary" display="block">
						≈{" "}
						{new Intl.NumberFormat("en-US", {
							style: "currency",
							currency,
							maximumFractionDigits: 2,
						}).format(monthlyReference)}{" "}
						/ month{discountPercent ? ` (Save ${discountPercent}%)` : ""}
					</Typography>
				)}
			</Box>
			<Divider />
			{/* Features list */}
			<Stack component="ul" spacing={1.5} sx={{ listStyle: "none", pl: 0, my: 3 }}>
				{features.map((feature) => {
					const clean = feature.replace(/ \*$/, "");
					return (
						<li key={feature}>
							<Stack direction="row" alignItems="center" spacing={1}>
								<CheckIcon size={16} />
								<Tooltip title={FEATURE_DETAILS?.[clean] || ""} placement="right" arrow>
									<Typography variant="body2">{feature}</Typography>
								</Tooltip>
							</Stack>
						</li>
					);
				})}
			</Stack>
			{/* Action button */}
			{action ?? (
				<Button
					variant={id === "business" ? "outlined" : "contained"}
					color="primary"
					size="large"
					fullWidth
					onClick={() => {
						if (id === "business") {
							globalThis?.dispatchEvent(new CustomEvent("pricing:contact", { detail: { plan: id } }));
							globalThis.location.href = "mailto:sales@example.com?subject=Business%20Plan%20Inquiry";
							return;
						}
						globalThis?.dispatchEvent(
							new CustomEvent("pricing:select", { detail: { plan: id, yearly: period === "/year" } })
						);
						if (onSelect) {
							onSelect(id);
						} else {
							setInternalSelected(true);
						}
					}}
				>
					{id === "business" ? "Contact us" : "Select"}
				</Button>
			)}
		</Card>
	);
}

// No custom icons defined here; you could add a PlanIcon component
// similar to the previous implementation if desired.
