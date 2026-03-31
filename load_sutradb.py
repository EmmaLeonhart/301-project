"""Load acquired data into SutraDB and run sample queries."""

import sys
import io
import pandas as pd

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from src.sutradb_store import (
    get_client, load_dataframe, query_domain_counts,
    query_p31_distribution, query_category_distribution, export_to_csv,
)


def main():
    client = get_client()
    print(f"SutraDB health: {client.health()}")

    # Load the processed data
    df = pd.read_csv("data/processed/ontology_comparison.csv")
    print(f"\nLoading {len(df)} items into SutraDB...")
    triple_count = load_dataframe(df, client)
    print(f"Inserted {triple_count} triples")

    # Query domain counts
    print("\n--- Items per domain (from SutraDB) ---")
    for row in query_domain_counts(client):
        print(f"  {row['domain']['value']}: {row['count']['value']}")

    # P31 class distribution
    print("\n--- Top P31 classes (from SutraDB) ---")
    for row in query_p31_distribution(client)[:10]:
        print(f"  {row['p31Class']['value']}: {row['count']['value']}")

    # Category distribution
    print("\n--- Top Wikipedia categories (from SutraDB) ---")
    for row in query_category_distribution(client)[:10]:
        print(f"  {row['cat']['value']}: {row['count']['value']}")

    # Export back to CSV
    export_df = export_to_csv("data/processed/sutradb_export.csv", client)
    print(f"\nExported {len(export_df)} items to data/processed/sutradb_export.csv")


if __name__ == "__main__":
    main()
