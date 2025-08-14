"""Utility functions for computing evaluation metrics.

These functions can be passed to evaluation pipelines or used
independently to compute accuracy, precision, recall and F1
scores. They operate on simple Python values and return floats
between 0 and 1.
"""

from __future__ import annotations

from collections import Counter
from difflib import SequenceMatcher
from typing import Any, Iterable, Tuple


def string_check(expected: str, predicted: str) -> float:
    """Return 1.0 if strings match exactly, otherwise 0.0."""
    return 1.0 if expected == predicted else 0.0


def similarity_ratio(a: str, b: str) -> float:
    """Compute a similarity ratio between two strings using SequenceMatcher."""
    return SequenceMatcher(None, a or "", b or "").ratio()


def precision_recall_f1(tp: int, fp: int, fn: int) -> Tuple[float, float, float]:
    """Compute precision, recall and F1 score given true/false positives and negatives."""
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    return precision, recall, f1


def count_binary(outcomes: Iterable[Tuple[bool, bool]]) -> Tuple[int, int, int, int]:
    """Count true positives, false positives, true negatives and false negatives.

    Each element of ``outcomes`` is a tuple of (expected, predicted).
    """
    tp = fp = tn = fn = 0
    for expected, predicted in outcomes:
        if expected and predicted:
            tp += 1
        elif not expected and predicted:
            fp += 1
        elif expected and not predicted:
            fn += 1
        else:
            tn += 1
    return tp, fp, tn, fn