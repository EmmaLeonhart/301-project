"""Main data acquisition script. Run this to fetch all data and save to CSV."""

import sys
import io
import os

# Windows Unicode fix
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from src.etl import build_all_domains
from src.analysis import p910_category_overlap, domain_summary


def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    print(f"Fetching up to {limit} items per domain...")

    df = build_all_domains(limit=limit, delay=1.0)
    df = p910_category_overlap(df)

    os.makedirs("data/processed", exist_ok=True)
    df.to_csv("data/processed/ontology_comparison.csv", index=False)
    print(f"\nSaved {len(df)} items to data/processed/ontology_comparison.csv")

    summary = domain_summary(df)
    summary.to_csv("data/processed/domain_summary.csv", index=False)
    print(f"Saved domain summary to data/processed/domain_summary.csv")
    print("\nDomain summary:")
    print(summary.to_string(index=False))

    # P910 depth stats
    if "p910_depth" in df.columns:
        found = df[df["p910_depth"] >= 0]
        not_found = df[df["p910_depth"] < 0]
        no_p910 = df[df["p910_count"] == 0]
        print(f"\nP910 category analysis:")
        print(f"  Items with P910-derived categories: {len(df) - len(no_p910)}/{len(df)}")
        print(f"  Direct match (depth 0): {len(found[found['p910_depth'] == 0])}")
        print(f"  Found in parent chain: {len(found[found['p910_depth'] > 0])}")
        print(f"  Not found within 5 hops: {len(not_found) - len(no_p910)}")
        print(f"  No P910 link on P31 class: {len(no_p910)}")
        if not found.empty:
            print(f"  Mean depth to match: {found['p910_depth'].mean():.2f}")
            print(f"\n  Per domain:")
            for domain, group in df.groupby("domain"):
                g_found = group[group["p910_depth"] >= 0]
                g_no_p910 = group[group["p910_count"] == 0]
                print(f"    {domain}: p910_linked={len(group) - len(g_no_p910)}/{len(group)}, "
                      f"direct_match={len(g_found[g_found['p910_depth'] == 0])}, "
                      f"found_in_chain={len(g_found[g_found['p910_depth'] > 0])}")


if __name__ == "__main__":
    main()
