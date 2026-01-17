"""Helpers for inferring and normalising receipt expense categories."""

from __future__ import annotations

from collections import OrderedDict
from typing import Iterable, Sequence

from app.models.schemas import LineItem, ReceiptDetails

UNCATEGORIZED = "Uncategorized"

# Keyword heuristics grouped by target category name. OrderedDict preserves priority.
_HEURISTIC_KEYWORDS: "OrderedDict[str, tuple[str, ...]]" = OrderedDict(
    [
        ("Travel", ("uber", "lyft", "airbnb", "hotel", "marriott", "hilton", "delta", "airlines", "airport")),
        ("Meals & Entertainment", ("restaurant", "grill", "cafe", "coffee", "bar", "pizza", "burger", "diner")),
        ("Transportation", ("taxi", "fuel", "gas", "gasoline", "shell", "chevron", "bp", "parking")),
        ("Software & Cloud", ("software", "subscription", "saas", "slack", "zoom", "github", "aws", "azure", "gcp")),
        ("Office Supplies", ("office", "stationery", "paper", "ink", "staples", "office depot")),
        # Home improvement / hardware retailers
        (
            "Supplies & Materials",
            (
                "home depot",
                "homedepot",
                "lowe's",
                "lowes",
                "ace hardware",
                "menards",
                "harbor freight",
                "harbour freight",
            ),
        ),
        ("Marketing", ("advertising", "ads", "google ads", "facebook ads", "meta ads", "campaign")),
        ("Utilities", ("utility", "internet", "electric", "water", "comcast", "verizon", "spectrum", "att")),
        ("Equipment", ("hardware", "laptop", "computer", "device", "electronics", "best buy", "apple")),
    ]
)


def normalize_categories(values: Iterable[str], *, include_fallback: bool = True) -> list[str]:
    """Clean a sequence of category labels, preserving order and removing duplicates.

    Args:
        values: Raw category labels from users or heuristics.
        include_fallback: When True and the cleaned list is empty, return ``["Uncategorized"]``.
    """
    seen: set[str] = set()
    cleaned: list[str] = []
    for raw in values:
        if not raw:
            continue
        label = " ".join(str(raw).split())
        if not label:
            continue
        if label.lower() == UNCATEGORIZED.lower():
            label = UNCATEGORIZED
        else:
            label = label.strip()
            if not label:
                continue
            # Title-case words while respecting all-caps abbreviations (e.g., "SaaS").
            parts = label.split(" ")
            normalised_parts: list[str] = []
            for part in parts:
                if len(part) <= 3 and part.isupper():
                    normalised_parts.append(part)
                else:
                    normalised_parts.append(part[:1].upper() + part[1:])
            label = " ".join(normalised_parts)
        lowered = label.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        cleaned.append(label)
    if len(cleaned) > 1:
        cleaned = [label for label in cleaned if label != UNCATEGORIZED]
    if include_fallback and not cleaned:
        return [UNCATEGORIZED]
    return cleaned


def _candidate_strings(items: Sequence[LineItem], merchant: str | None) -> list[str]:
    """Collect strings that may contain category hints."""
    candidates: list[str] = []
    if merchant:
        candidates.append(merchant)
    for item in items:
        if item.description:
            candidates.append(item.description)
    return candidates


def infer_categories(details: ReceiptDetails) -> list[str]:
    """Infer likely categories from extracted receipt details.

    New strategy (no reliance on item.category):
    - Use merchant- and description-keyword heuristics only.
    - Prefer merchant matches over description matches by virtue of ordering in
      ``_candidate_strings`` (merchant comes first), but allow multiple matches.
    Always returns a possibly-empty list; caller should apply ``normalize_categories``.
    """
    inferred: list[str] = []
    # Heuristic classification from merchant and line-item descriptions only (ignore item.category)
    candidates = _candidate_strings(details.items, details.merchant)
    lowered_candidates = [c.lower() for c in candidates if c]
    for category, keywords in _HEURISTIC_KEYWORDS.items():
        for text in lowered_candidates:
            if any(keyword in text for keyword in keywords):
                inferred.append(category)
                break
    return inferred


__all__ = ["infer_categories", "normalize_categories", "UNCATEGORIZED"]
