"""Analysis functions for comparing Wikidata P31 vs Wikipedia categories."""

import pandas as pd


def _substring_match(p31_labels: set[str], wiki_cats: set[str]) -> set[str]:
    """Return P31 labels that appear as a substring in any Wikipedia category.

    E.g. "film" matches "2020 films", "city" matches "Cities in Germany".
    Case-insensitive.
    """
    matched = set()
    cats_joined = [c.lower() for c in wiki_cats]
    for label in p31_labels:
        label_lower = label.lower()
        for cat in cats_joined:
            if label_lower in cat or cat in label_lower:
                matched.add(label)
                break
    return matched


def p31_category_overlap(df: pd.DataFrame) -> pd.DataFrame:
    """For each item, compute how many P31 class labels appear in Wikipedia categories.

    Uses substring matching: "film" matches "2020 films", etc.
    Adds columns: overlap_count, overlap_ratio (overlap / p31_count).
    """
    overlaps = []
    for _, row in df.iterrows():
        p31_labels = set(row["p31_classes"].split("|")) if row["p31_classes"] else set()
        wiki_cats = set(row["wikipedia_categories"].split("|")) if row["wikipedia_categories"] else set()

        matched = _substring_match(p31_labels, wiki_cats)

        overlaps.append({
            "qid": row["qid"],
            "overlap_count": len(matched),
            "overlap_labels": "|".join(sorted(matched)),
            "overlap_ratio": len(matched) / len(p31_labels) if p31_labels else 0.0,
        })

    overlap_df = pd.DataFrame(overlaps)
    return df.merge(overlap_df, on="qid")


def domain_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Summarize overlap statistics per domain."""
    if "overlap_ratio" not in df.columns:
        df = p31_category_overlap(df)

    return df.groupby("domain").agg(
        item_count=("qid", "count"),
        mean_p31_count=("p31_count", "mean"),
        mean_category_count=("category_count", "mean"),
        mean_overlap_ratio=("overlap_ratio", "mean"),
        median_overlap_ratio=("overlap_ratio", "median"),
    ).reset_index()
