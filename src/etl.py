"""ETL: merge Wikidata P31 data with Wikipedia categories, clean, and export."""

import pandas as pd

from src.wikidata import fetch_domain, DOMAINS
from src.wikipedia import fetch_categories


def build_dataset(domain_name: str, limit: int = 500, delay: float = 1.0) -> pd.DataFrame:
    """Fetch and merge Wikidata + Wikipedia data for a domain.

    Returns a DataFrame with columns:
        qid, label, enwiki_title, domain, p31_classes, wikipedia_categories
    """
    items = fetch_domain(domain_name, limit=limit, delay=delay)

    rows = []
    for item in items:
        cats = fetch_categories(item["enwiki_title"])
        p31_labels = [c["label"] for c in item["p31_classes"]]
        rows.append({
            "qid": item["qid"],
            "label": item["label"],
            "enwiki_title": item["enwiki_title"],
            "domain": item["domain"],
            "p31_classes": "|".join(p31_labels),
            "p31_qids": "|".join(c["qid"] for c in item["p31_classes"]),
            "wikipedia_categories": "|".join(cats),
            "p31_count": len(p31_labels),
            "category_count": len(cats),
        })

    return pd.DataFrame(rows)


def build_all_domains(limit: int = 100, delay: float = 1.0) -> pd.DataFrame:
    """Build dataset across all configured domains."""
    frames = []
    for domain_name in DOMAINS:
        print(f"Fetching domain: {domain_name}")
        df = build_dataset(domain_name, limit=limit, delay=delay)
        frames.append(df)
        print(f"  Got {len(df)} items for {domain_name}")
    return pd.concat(frames, ignore_index=True)
