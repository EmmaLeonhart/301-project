"""ETL: merge Wikidata P31/P910 data with Wikipedia categories and export."""

import pandas as pd

from src.wikidata import fetch_domain, fetch_p910_chain, DOMAINS
from src.wikipedia import fetch_categories, fetch_category_chain
from src.analysis import compute_category_depth


def build_dataset(domain_name: str, limit: int = 500, delay: float = 1.0) -> pd.DataFrame:
    """Fetch and merge Wikidata + Wikipedia data for a domain.

    Uses the P910 approach:
    1. Get each item's P31 (instance of) classes
    2. For each P31 class, follow P910 (topic's main category) to get a Wikidata category item
    3. Use that category item's enwiki sitelink to get the actual Wikipedia category name
    4. Check whether the item is in that Wikipedia category (directly or via parent chain)
    """
    items = fetch_domain(domain_name, limit=limit, delay=delay)

    # Collect all unique P31 QIDs across this domain
    p31_qid_set = set()
    for item in items:
        for c in item["p31_classes"]:
            p31_qid_set.add(c["qid"])

    # Fetch P910 links for all P31 classes (walking up P279 if needed)
    print(f"  Fetching P910 category links for {len(p31_qid_set)} unique P31 classes...")
    p910_results = fetch_p910_chain(list(p31_qid_set), max_depth=3, delay=delay)

    # Build lookup: P31 QID -> set of enwiki category names (from P910)
    p910_by_class: dict[str, set[str]] = {}
    p910_depth_by_class: dict[str, dict[str, int]] = {}  # class -> {cat_name: depth}
    for entry in p910_results:
        cls = entry["source_class"]
        cat = entry["enwiki_category"]
        depth = entry["depth"]
        if cls not in p910_by_class:
            p910_by_class[cls] = set()
            p910_depth_by_class[cls] = {}
        p910_by_class[cls].add(cat)
        # Keep the shallowest depth for each category
        if cat not in p910_depth_by_class[cls] or depth < p910_depth_by_class[cls][cat]:
            p910_depth_by_class[cls][cat] = depth

    # Fetch Wikipedia categories for each item
    cat_per_item = {}
    for item in items:
        cats = fetch_categories(item["enwiki_title"])
        cat_per_item[item["qid"]] = cats

    # Fetch parent category chains for depth analysis
    all_categories = set()
    for cats in cat_per_item.values():
        all_categories.update(cats)

    print(f"  Fetching parent categories for {len(all_categories)} unique categories...")
    combined_chain = fetch_category_chain(list(all_categories), max_depth=5, delay=0.5)

    rows = []
    for item in items:
        cats = cat_per_item[item["qid"]]
        p31_labels = [c["label"] for c in item["p31_classes"]]
        p31_qids = [c["qid"] for c in item["p31_classes"]]

        # Collect all P910-derived Wikipedia categories for this item's P31 classes
        # and track the minimum P279 depth needed to reach a P910 link
        expected_cats = set()
        min_p279_depth = float("inf")
        for p31_qid in p31_qids:
            if p31_qid in p910_by_class:
                expected_cats.update(p910_by_class[p31_qid])
                for cat, d in p910_depth_by_class[p31_qid].items():
                    if d < min_p279_depth:
                        min_p279_depth = d
        if min_p279_depth == float("inf"):
            min_p279_depth = -1

        # Build Wikipedia category hierarchy for this item
        wp_levels: dict[int, list[str]] = {0: cats}
        for depth, parent_cats in combined_chain.items():
            wp_levels[depth] = parent_cats

        # Check how deep we need to go to find the P910-derived category
        depth_result = compute_category_depth(expected_cats, wp_levels)

        rows.append({
            "qid": item["qid"],
            "label": item["label"],
            "enwiki_title": item["enwiki_title"],
            "domain": item["domain"],
            "p31_classes": "|".join(p31_labels),
            "p31_qids": "|".join(p31_qids),
            "p910_categories": "|".join(sorted(expected_cats)),
            "p910_count": len(expected_cats),
            "wikipedia_categories": "|".join(cats),
            "p31_count": len(p31_labels),
            "category_count": len(cats),
            "p279_depth": int(min_p279_depth),
            "wp_depth": depth_result["min_depth"],
            "p910_depth": (int(min_p279_depth) + depth_result["min_depth"]) if min_p279_depth >= 0 and depth_result["min_depth"] >= 0 else -1,
            "p910_matched_category": depth_result["matched_category"],
        })

    return pd.DataFrame(rows)


def build_all_domains(limit: int = 100, delay: float = 1.0) -> pd.DataFrame:
    """Build dataset across all configured domains.

    Catches per-domain errors so that a failure in one domain does not
    prevent the rest from being collected and saved.
    """
    frames = []
    for domain_name in DOMAINS:
        print(f"Fetching domain: {domain_name}")
        try:
            df = build_dataset(domain_name, limit=limit, delay=delay)
            frames.append(df)
            print(f"  Got {len(df)} items for {domain_name}")
        except Exception as e:
            print(f"  ERROR fetching {domain_name}: {e} — skipping")
    if not frames:
        raise RuntimeError("All domains failed to fetch")
    return pd.concat(frames, ignore_index=True)
