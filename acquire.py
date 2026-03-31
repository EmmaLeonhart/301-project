"""Main data acquisition script. Run this to fetch all data and save to CSV."""

import sys
import io
import os

# Windows Unicode fix
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from src.etl import build_all_domains
from src.analysis import p31_category_overlap, domain_summary


def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    print(f"Fetching up to {limit} items per domain...")

    df = build_all_domains(limit=limit, delay=1.0)
    df = p31_category_overlap(df)

    os.makedirs("data/processed", exist_ok=True)
    df.to_csv("data/processed/ontology_comparison.csv", index=False)
    print(f"\nSaved {len(df)} items to data/processed/ontology_comparison.csv")

    summary = domain_summary(df)
    summary.to_csv("data/processed/domain_summary.csv", index=False)
    print(f"Saved domain summary to data/processed/domain_summary.csv")
    print("\nDomain summary:")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
