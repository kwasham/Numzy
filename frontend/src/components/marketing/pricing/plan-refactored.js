import Box from "@mui/material/Box";
import Card from "@mui/material/Card";
import Chip from "@mui/material/Chip";
import Divider from "@mui/material/Divider";
import Stack from "@mui/material/Stack";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import { CheckIcon } from "@phosphor-icons/react/dist/ssr/Check";

import { FEATURE_DETAILS } from "./pricing-config-refactored";

/**
 * A pricing card representing a single plan.  This refactored version adds
 * handling for the new `enterprise` tier and displays a "Custom pricing"
 * label when the plan price is zero.  Other logic remains unchanged.
 */
export function Plan({
	action,
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
}) {
	const priceDisplay =
		price === 0 && id === "enterprise"
			? "Custom pricing"
			: new Intl.NumberFormat("en-US", {
					style: "currency",
					currency,
					maximumFractionDigits: price === 0 ? 0 : 2,
				}).format(price);
	return (
		<Card data-pricing-card="true" data-plan={id}>
			{recommended && <Chip label="Recommended" color="primary" size="small" sx={{ mb: 1 }} />}
			<Stack spacing={1}>
				<Typography variant="h5" component="h3">
					{name}
				</Typography>
				<Typography variant="subtitle1" color="text.secondary">
					{description}
				</Typography>
				<Box>
					<Typography variant="h4" component="span">
						{priceDisplay}
					</Typography>
					{price !== 0 && <Typography component="span">{period}</Typography>}
					{period === "/year" && monthlyReference != null && (
						<Typography variant="caption" color="text.secondary">
							≈{" "}
							{new Intl.NumberFormat("en-US", { style: "currency", currency, maximumFractionDigits: 2 }).format(
								monthlyReference
							)}{" "}
							/ month
							{discountPercent ? ` (Save ${discountPercent}%)` : ""}
						</Typography>
					)}
				</Box>
				<Divider />
				<Stack component="ul" spacing={1} sx={{ listStyle: "none", pl: 0 }}>
					{features.map((feature) => (
						<li key={feature}>
							<Stack direction="row" alignItems="center" spacing={1}>
								<CheckIcon size={16} />
								<Tooltip title={FEATURE_DETAILS[feature] || ""} placement="right" arrow>
									<Typography variant="body2">{feature}</Typography>
								</Tooltip>
							</Stack>
						</li>
					))}
				</Stack>
				{action}
			</Stack>
		</Card>
	);
}
