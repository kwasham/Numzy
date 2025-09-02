// Feature gating utilities for Numzy
//
// This helper module centralizes logic for checking whether a given
// subscription plan includes a specific feature.  It allows both
// frontend and backend code to guard access to functionality based on
// the canonical pricing catalog.  If additional gating rules are
// required (e.g. quota checks, time‑limited trials), they can be added
// here without scattering conditional logic throughout the codebase.

import { PRICING_CATALOG } from "./catalog";

/**
 * Determine whether a subscription plan includes the given feature.
 *
 * @param {string} planId - The identifier of the plan (e.g. "personal", "pro").
 * @param {string} feature - The human‑readable feature string to check.
 * @returns {boolean} true if the feature is listed for the plan; false otherwise.
 */
export function hasFeature(planId, feature) {
  const entry = PRICING_CATALOG[planId];
  if (!entry || !Array.isArray(entry.features)) {
    return false;
  }
  return entry.features.includes(feature);
}

/**
 * Enforce that a plan contains a feature.  Useful in backend route
 * handlers where unauthorised access should result in an error.
 *
 * Throws an error if the feature is not present; otherwise returns
 * silently.  Consumers can catch the error to handle denial logic.
 *
 * @param {string} planId
 * @param {string} feature
 */
export function ensureFeature(planId, feature) {
  if (!hasFeature(planId, feature)) {
    throw new Error(`Plan '${planId}' does not include feature '${feature}'`);
  }
}

/**
 * Retrieve the list of feature strings for a given plan.  This
 * function returns a new array to avoid accidental mutation of the
 * underlying catalog.
 *
 * @param {string} planId
 * @returns {string[]} the feature list, or an empty array if the plan
 * is not defined.
 */
export function getPlanFeatures(planId) {
  const entry = PRICING_CATALOG[planId];
  return entry && Array.isArray(entry.features) ? [...entry.features] : [];
}

/**
 * Check whether the current user can access a given feature.  This
 * helper expects a user object with a `planId` property; it returns
 * false if the user is undefined or the plan lacks the feature.  When
 * building UI components, use this to conditionally render controls
 * based on the user’s subscription tier.
 *
 * @param {{ planId?: string } | null | undefined} user
 * @param {string} feature
 * @returns {boolean}
 */
export function userHasFeature(user, feature) {
  if (!user || typeof user.planId !== "string") {
    return false;
  }
  return hasFeature(user.planId, feature);
}