"""Analysis functions for comparing Wikidata P31 vs Wikipedia categories."""

import pandas as pd


def p31_category_overlap(df: pd.DataFrame) -> pd.DataFrame:
    """For each item, compute how many P31 class labels appear in Wikipedia categories.

    Adds columns: overlap_count, overlap_ratio (overlap / p31_count).
    """
    overlaps = []
    for _, row in df.iterrows():
        p31_labels = set(row["p31_classes"].split("|")) if row["p31_classes"] else set()
        wiki_cats = set(row["wikipedia_categories"].split("|")) if row["wikipedia_categories"] else set()

        # Case-insensitive comparison
        p31_lower = {s.lower() for s in p31_labels}
        cats_lower = {s.lower() for s in wiki_cats}
        overlap = p31_lower & cats_lower

        overlaps.append({
            "qid": row["qid"],
            "overlap_count": len(overlap),
            "overlap_labels": "|".join(sorted(overlap)),
            "overlap_ratio": len(overlap) / len(p31_lower) if p31_lower else 0.0,
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
