"""ETL: merge Wikidata P31 data with Wikipedia categories, clean, and export."""

import pandas as pd

from src.wikidata import fetch_domain, fetch_p279_chain, fetch_p31_values, DOMAINS
from src.wikipedia import fetch_categories, fetch_category_chain
from src.analysis import compute_hop_distance


def build_dataset(domain_name: str, limit: int = 500, delay: float = 1.0) -> pd.DataFrame:
    """Fetch and merge Wikidata + Wikipedia data for a domain.

    Returns a DataFrame with columns:
        qid, label, enwiki_title, domain, p31_classes, wikipedia_categories,
        total_hops, hops_wikidata, hops_wikipedia, match_label, match_category
    """
    items = fetch_domain(domain_name, limit=limit, delay=delay)

    # Collect all unique P31 QIDs across this domain for batch P279 traversal
    p31_qid_set = set()
    for item in items:
        for c in item["p31_classes"]:
            p31_qid_set.add(c["qid"])

    # Cache: P279 ancestor chain per unique P31 QID
    # {qid: {0: [{'qid': ..., 'label': ...}], 1: [...], ...}}
    print(f"  Fetching P279 hierarchy for {len(p31_qid_set)} unique P31 classes...")
    p279_cache: dict[str, dict[int, list[dict]]] = {}
    for p31_qid in p31_qid_set:
        # Level 0 is the P31 value itself — we need its label
        p31_info = [c for item in items for c in item["p31_classes"] if c["qid"] == p31_qid]
        p31_label = p31_info[0]["label"] if p31_info else p31_qid
        chain = fetch_p279_chain([p31_qid], max_depth=5, delay=delay)
        chain[0] = [{"qid": p31_qid, "label": p31_label}]
        p279_cache[p31_qid] = chain

    # Cache: Wikipedia parent category chain per unique category
    all_categories = set()
    cat_per_item = {}
    for item in items:
        cats = fetch_categories(item["enwiki_title"])
        cat_per_item[item["qid"]] = cats
        all_categories.update(cats)

    print(f"  Fetching parent categories for {len(all_categories)} unique categories...")
    wp_cache: dict[str, dict[int, list[str]]] = {}
    cat_list = list(all_categories)
    # Batch fetch parent chains — but each category's chain is independent,
    # so we do a shared BFS from ALL categories at once, then split out per-category.
    # Simpler approach: just fetch the combined chain and tag per starting category.
    # Actually simplest: fetch one shared chain, use it for all items.
    # Each item only cares about "at depth N from my categories, what's available?"
    # So we can compute per-item levels by combining their specific starting categories
    # with the shared parent chain.

    # Build a shared BFS from all categories
    combined_chain = fetch_category_chain(cat_list, max_depth=5, delay=0.5)

    rows = []
    for item in items:
        cats = cat_per_item[item["qid"]]
        p31_labels = [c["label"] for c in item["p31_classes"]]
        p31_qids = [c["qid"] for c in item["p31_classes"]]

        # Build Wikidata levels for this item: merge P279 chains from all its P31 values
        wd_levels: dict[int, list[str]] = {}
        for p31_qid in p31_qids:
            if p31_qid in p279_cache:
                for depth, ancestors in p279_cache[p31_qid].items():
                    if depth not in wd_levels:
                        wd_levels[depth] = []
                    wd_levels[depth].extend(a["label"] for a in ancestors)

        # Build Wikipedia levels for this item
        # Depth 0 = the item's direct categories
        # Depth 1+ = from the combined BFS (shared across all items)
        wp_levels: dict[int, list[str]] = {0: cats}
        for depth, parent_cats in combined_chain.items():
            wp_levels[depth] = parent_cats

        # Compute hop distance
        hop = compute_hop_distance(wd_levels, wp_levels)

        rows.append({
            "qid": item["qid"],
            "label": item["label"],
            "enwiki_title": item["enwiki_title"],
            "domain": item["domain"],
            "p31_classes": "|".join(p31_labels),
            "p31_qids": "|".join(p31_qids),
            "wikipedia_categories": "|".join(cats),
            "p31_count": len(p31_labels),
            "category_count": len(cats),
            "total_hops": hop["total_hops"],
            "hops_wikidata": hop["hops_wikidata"],
            "hops_wikipedia": hop["hops_wikipedia"],
            "match_label": hop["match_label"],
            "match_category": hop["match_category"],
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
