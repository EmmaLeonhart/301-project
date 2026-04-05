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


def compute_hop_distance(wd_levels: dict[int, list[str]], wp_levels: dict[int, list[str]]) -> dict:
    """Find the minimum total hops for a Wikidata ancestor to match a Wikipedia ancestor.

    wd_levels: {0: ['film'], 1: ['visual artwork', 'creative work'], ...}
               (depth -> list of Wikidata class labels at that depth)
    wp_levels: {0: ['2020 films', 'Drama films'], 1: ['Films by year'], ...}
               (depth -> list of Wikipedia category names at that depth)

    We check all (wd_depth, wp_depth) pairs ordered by total_hops = wd_depth + wp_depth.
    The first substring match found is the convergence point.

    Returns dict with: total_hops, hops_wikidata, hops_wikipedia, match_label, match_category.
    Returns total_hops=-1 if no convergence found.
    """
    max_wd = max(wd_levels.keys(), default=0)
    max_wp = max(wp_levels.keys(), default=0)

    for total in range(0, max_wd + max_wp + 1):
        for wd_d in range(min(total, max_wd) + 1):
            wp_d = total - wd_d
            if wd_d not in wd_levels or wp_d not in wp_levels:
                continue
            for label in wd_levels[wd_d]:
                label_lower = label.lower()
                for cat in wp_levels[wp_d]:
                    cat_lower = cat.lower()
                    if label_lower in cat_lower or cat_lower in label_lower:
                        return {
                            "total_hops": total,
                            "hops_wikidata": wd_d,
                            "hops_wikipedia": wp_d,
                            "match_label": label,
                            "match_category": cat,
                        }

    return {
        "total_hops": -1,
        "hops_wikidata": -1,
        "hops_wikipedia": -1,
        "match_label": "",
        "match_category": "",
    }


def domain_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Summarize overlap statistics per domain."""
    if "overlap_ratio" not in df.columns:
        df = p31_category_overlap(df)

    aggs = {
        "item_count": ("qid", "count"),
        "mean_p31_count": ("p31_count", "mean"),
        "mean_category_count": ("category_count", "mean"),
        "mean_overlap_ratio": ("overlap_ratio", "mean"),
        "median_overlap_ratio": ("overlap_ratio", "median"),
    }
    if "total_hops" in df.columns:
        converged = df[df["total_hops"] >= 0]
        if not converged.empty:
            aggs["mean_hops"] = ("total_hops", "mean")
            aggs["median_hops"] = ("total_hops", "median")

    return df.groupby("domain").agg(**aggs).reset_index()
