"""Analysis functions for comparing Wikidata P31 (via P910) with Wikipedia categories."""

import pandas as pd


def p910_category_overlap(df: pd.DataFrame) -> pd.DataFrame:
    """For each item, check how many P910-derived categories appear in its Wikipedia categories.

    The P910 approach: P31 class → P910 (topic's main category) → enwiki sitelink.
    This gives us the actual Wikipedia category that Wikidata says the item should be in.
    We then check if the item is actually in that category.

    Adds columns: overlap_count, overlap_ratio, matched_categories.
    """
    overlaps = []
    for _, row in df.iterrows():
        p910_cats = set(row["p910_categories"].split("|")) if row["p910_categories"] else set()
        wiki_cats = set(row["wikipedia_categories"].split("|")) if row["wikipedia_categories"] else set()

        matched = p910_cats & wiki_cats

        overlaps.append({
            "qid": row["qid"],
            "overlap_count": len(matched),
            "matched_categories": "|".join(sorted(matched)),
            "overlap_ratio": len(matched) / len(p910_cats) if p910_cats else 0.0,
        })

    overlap_df = pd.DataFrame(overlaps)
    return df.merge(overlap_df, on="qid")


def compute_category_depth(p910_cats: set, wp_levels: dict[int, list[str]]) -> dict:
    """Find the minimum depth at which a P910-derived category appears in the Wikipedia hierarchy.

    wp_levels: {0: [direct categories], 1: [parent categories], 2: [...], ...}
    p910_cats: set of expected Wikipedia category names (from P910 links)

    Returns dict with: min_depth (0 if direct match, >0 if found in ancestors, -1 if not found),
    matched_category (the category that matched).
    """
    for depth in sorted(wp_levels.keys()):
        cats_at_depth = set(wp_levels[depth])
        matched = p910_cats & cats_at_depth
        if matched:
            return {
                "min_depth": depth,
                "matched_category": sorted(matched)[0],
            }

    return {
        "min_depth": -1,
        "matched_category": "",
    }


def domain_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Summarize overlap statistics per domain."""
    if "overlap_ratio" not in df.columns:
        df = p910_category_overlap(df)

    aggs = {
        "item_count": ("qid", "count"),
        "mean_p31_count": ("p31_count", "mean"),
        "mean_category_count": ("category_count", "mean"),
        "mean_overlap_ratio": ("overlap_ratio", "mean"),
        "median_overlap_ratio": ("overlap_ratio", "median"),
        "mean_p910_count": ("p910_count", "mean"),
    }

    if "p910_depth" in df.columns:
        found = df[df["p910_depth"] >= 0]
        if not found.empty:
            aggs["mean_depth"] = ("p910_depth", "mean")
            aggs["median_depth"] = ("p910_depth", "median")

    return df.groupby("domain").agg(**aggs).reset_index()
