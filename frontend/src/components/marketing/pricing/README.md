# Pricing Components

Unified pricing implementation.

## Files

- `pricing-config.js`: Derived exports (numbers, metadata, features) from shared `shared/pricing/catalog.js`.
- `plan.js`: Unified Plan card component (selection, accessibility, enterprise custom pricing, tooltips).
- `plans-table.js`: Table with annual billing toggle, selection persistence, impression + analytics events, feature delta mapping, JSON-LD markup.
- `__tests__/`: Minimal tests for Plan and PlansTable.
- `__tests__/catalog-mapping.test.ts`: Asserts derived config stays in sync with shared catalog.

Shared cross-package source of truth lives in `shared/pricing/catalog.js`. A helper script `shared/pricing/build-pricing-json.mjs` outputs a backend-friendly JSON snapshot (run via `node shared/pricing/build-pricing-json.mjs > pricing-snapshot.json`).

## Legend

`*` after a feature indicates the feature first appears at that tier.

## Extending

- Add new plan: edit `shared/pricing/catalog.js` only (id, pricing, discount, description, features, quota, recommended). Then run tests; derived exports update automatically.
- To hide a feature tooltip, remove entry from `FEATURE_DETAILS` (empty string yields no tooltip).
- Replace mailto in Plan with a modal for enterprise contact if needed.

## TODO (Future Enhancements)

- Add analytics batching and debounce.
- Add visual toggle for monthly vs yearly savings on each card.
- Extract accent colors to theme tokens.
- Add script to diff `catalog.js` against Webflow CMS and optionally sync.
