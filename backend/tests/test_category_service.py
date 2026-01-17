from app.models.schemas import LineItem, ReceiptDetails
from app.services.category_service import infer_categories, normalize_categories, UNCATEGORIZED


def test_infer_categories_uses_keywords_even_if_item_has_category():
    details = ReceiptDetails(
        merchant="Generic Store",
        items=[LineItem(category="Office Supplies"), LineItem(description="Printer paper")],
    )

    inferred = infer_categories(details)
    cleaned = normalize_categories(inferred)

    # Should still infer via keyword heuristics ("paper" -> Office Supplies), not rely on item.category
    assert cleaned and cleaned[0] == "Office Supplies"


def test_infer_categories_uses_keyword_heuristics():
    details = ReceiptDetails(
        merchant="Uber Technologies",
        items=[LineItem(description="Airport ride to conference")],
    )

    inferred = infer_categories(details)
    cleaned = normalize_categories(inferred)

    assert cleaned and cleaned[0] == "Travel"


def test_infer_categories_handles_harbour_freight_variant():
    details = ReceiptDetails(
        merchant="HARBOUR FREIGHT",
        items=[
            LineItem(description="3M N95 Respirator", total="$30.99"),
            LineItem(description="Cranium Puzzler", total="$4.99"),
        ],
    )

    inferred = infer_categories(details)
    cleaned = normalize_categories(inferred)

    assert cleaned and cleaned[0] == "Supplies & Materials"


def test_normalize_categories_deduplicates_and_handles_uncategorized():
    cleaned = normalize_categories(["Uncategorized", "meals & entertainment", "Meals & Entertainment"])

    assert cleaned == ["Meals & Entertainment"]

    fallback = normalize_categories([], include_fallback=True)
    assert fallback == [UNCATEGORIZED]

    no_fallback = normalize_categories([], include_fallback=False)
    assert no_fallback == []
