import Box from "@mui/material/Box";
import Card from "@mui/material/Card";
import Chip from "@mui/material/Chip";
import Divider from "@mui/material/Divider";
import Stack from "@mui/material/Stack";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import Button from "@mui/material/Button";
import { CheckIcon } from "@phosphor-icons/react/dist/ssr/Check";

import { FEATURE_DETAILS } from "./pricing-config-refactored";

/**
 * A polished pricing card component with improved styling.  This version
 * introduces base and highlighted styles, an accent bar to differentiate
 * tiers, and hover effects for better interactivity.  It also uses
 * responsive typography and consistent spacing to create a clean layout.
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
  // Define base and recommended styles.  These leverage the MUI theme
  // palette so colors automatically adjust between light/dark modes.
  const baseStyles = {
    backgroundColor: (theme) => theme.palette.grey[900],
    borderRadius: 2,
    border: '1px solid',
    borderColor: 'divider',
    boxShadow: 4,
    p: 3,
    transition: 'transform 0.2s ease, box-shadow 0.2s ease',
    '&:hover': {
      boxShadow: 8,
      transform: 'translateY(-2px)',
    },
  };

  const recommendedStyles = {
    ...baseStyles,
    borderColor: 'primary.main',
    transform: 'scale(1.03)',
    zIndex: 1,
  };

  // Accent bar colors keyed by plan id for quick customization.
  const accentColorMap = {
    free: 'info.main',
    personal: 'success.main',
    pro: 'primary.main',
    business: 'warning.main',
    enterprise: 'secondary.main',
  };

  // Convert price to display string; enterprise uses custom pricing label.
  const priceDisplay = price === 0 && id === 'enterprise'
    ? 'Custom pricing'
    : new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency,
        maximumFractionDigits: price === 0 ? 0 : 2,
      }).format(price);

  return (
    <Card
      data-pricing-card="true"
      data-plan={id}
      sx={recommended ? recommendedStyles : baseStyles}
    >
      {/* Accent bar */}
      <Box
        sx={{
          height: 4,
          backgroundColor: accentColorMap[id] || 'divider',
          borderTopLeftRadius: 8,
          borderTopRightRadius: 8,
          mb: 2,
        }}
      />
      {/* Recommended badge */}
      {recommended && (
        <Chip
          label="Recommended"
          color="primary"
          size="small"
          sx={{ mb: 1 }}
        />
      )}
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
        {period === '/year' && monthlyReference != null && (
          <Typography variant="caption" color="text.secondary" display="block">
            ≈ {new Intl.NumberFormat('en-US', {
              style: 'currency',
              currency,
              maximumFractionDigits: 2,
            }).format(monthlyReference)}{' '}
            / month{discountPercent ? ` (Save ${discountPercent}%)` : ''}
          </Typography>
        )}
      </Box>
      <Divider />
      {/* Features list */}
      <Stack component="ul" spacing={1.5} sx={{ listStyle: 'none', pl: 0, my: 3 }}>
        {features.map((feature) => (
          <li key={feature}>
            <Stack direction="row" alignItems="center" spacing={1}>
              <CheckIcon size={16} />
              <Tooltip title={FEATURE_DETAILS[feature] || ''} placement="right" arrow>
                <Typography variant="body2">{feature}</Typography>
              </Tooltip>
            </Stack>
          </li>
        ))}
      </Stack>
      {/* Action button */}
      <Button
        variant={id === 'business' ? 'outlined' : 'contained'}
        color="primary"
        size="large"
        fullWidth
        onClick={() => {
          // Dispatch custom events to allow parent components to handle actions.
          const eventName = id === 'business' ? 'pricing:contact' : 'pricing:select';
          globalThis?.dispatchEvent(
            new CustomEvent(eventName, { detail: { plan: id, yearly: period === '/year' } })
          );
        }}
      >
        {id === 'business' ? 'Contact us' : 'Select'}
      </Button>
    </Card>
  );
}

// No custom icons defined here; you could add a PlanIcon component
// similar to the previous implementation if desired.