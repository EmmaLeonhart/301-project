"""Load and query ontology comparison data in SutraDB."""

import pandas as pd
from sutradb import SutraClient

SUTRA_URL = "http://localhost:3030"
PREFIX = "http://cosc301.example.org/"
WD = "http://www.wikidata.org/entity/"
SCHEMA = "http://cosc301.example.org/schema/"


def get_client() -> SutraClient:
    return SutraClient(SUTRA_URL)


def _escape_literal(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def load_dataframe(df: pd.DataFrame, client: SutraClient | None = None):
    """Load ontology comparison DataFrame into SutraDB as RDF triples."""
    if client is None:
        client = get_client()

    triples = []
    for _, row in df.iterrows():
        qid = row["qid"]
        subj = f"<{WD}{qid}>"

        # Basic properties
        triples.append(f'{subj} <{SCHEMA}label> "{_escape_literal(str(row["label"]))}" .')
        triples.append(f'{subj} <{SCHEMA}enwikiTitle> "{_escape_literal(str(row["enwiki_title"]))}" .')
        triples.append(f'{subj} <{SCHEMA}domain> "{_escape_literal(str(row["domain"]))}" .')
        triples.append(f'{subj} <{SCHEMA}p31Count> "{row["p31_count"]}"^^<http://www.w3.org/2001/XMLSchema#integer> .')
        triples.append(f'{subj} <{SCHEMA}categoryCount> "{row["category_count"]}"^^<http://www.w3.org/2001/XMLSchema#integer> .')

        # P31 classes as separate triples
        if row["p31_classes"]:
            for cls in str(row["p31_classes"]).split("|"):
                if cls:
                    triples.append(f'{subj} <{SCHEMA}p31Class> "{_escape_literal(cls)}" .')

        # Wikipedia categories as separate triples
        if row["wikipedia_categories"]:
            for cat in str(row["wikipedia_categories"]).split("|"):
                if cat:
                    triples.append(f'{subj} <{SCHEMA}wikipediaCategory> "{_escape_literal(cat)}" .')

        # P31 QIDs as linked entities
        if row["p31_qids"]:
            for p31_qid in str(row["p31_qids"]).split("|"):
                if p31_qid:
                    triples.append(f'{subj} <{SCHEMA}p31Entity> <{WD}{p31_qid}> .')

    # Insert in batches to avoid overwhelming the server
    batch_size = 100
    for i in range(0, len(triples), batch_size):
        batch = "\n".join(triples[i:i + batch_size])
        client.insert_triples(batch)

    return len(triples)


def query_domain_counts(client: SutraClient | None = None) -> list[dict]:
    """Query SutraDB for item counts per domain."""
    if client is None:
        client = get_client()

    query = f"""
    SELECT ?domain (COUNT(DISTINCT ?item) AS ?count)
    WHERE {{
        ?item <{SCHEMA}domain> ?domain .
    }}
    GROUP BY ?domain
    ORDER BY DESC(?count)
    """
    result = client.sparql(query)
    return result["results"]["bindings"]


def query_items_by_domain(domain: str, client: SutraClient | None = None) -> list[dict]:
    """Query all items in a domain with their P31 classes and categories."""
    if client is None:
        client = get_client()

    query = f"""
    SELECT ?item ?label ?p31Count ?categoryCount
    WHERE {{
        ?item <{SCHEMA}domain> "{domain}" .
        ?item <{SCHEMA}label> ?label .
        ?item <{SCHEMA}p31Count> ?p31Count .
        ?item <{SCHEMA}categoryCount> ?categoryCount .
    }}
    ORDER BY ?label
    """
    result = client.sparql(query)
    return result["results"]["bindings"]


def query_p31_distribution(client: SutraClient | None = None) -> list[dict]:
    """Query how often each P31 class appears across all items."""
    if client is None:
        client = get_client()

    query = f"""
    SELECT ?p31Class (COUNT(?item) AS ?count)
    WHERE {{
        ?item <{SCHEMA}p31Class> ?p31Class .
    }}
    GROUP BY ?p31Class
    ORDER BY DESC(?count)
    """
    result = client.sparql(query)
    return result["results"]["bindings"]


def query_category_distribution(client: SutraClient | None = None) -> list[dict]:
    """Query how often each Wikipedia category appears across all items."""
    if client is None:
        client = get_client()

    query = f"""
    SELECT ?cat (COUNT(?item) AS ?count)
    WHERE {{
        ?item <{SCHEMA}wikipediaCategory> ?cat .
    }}
    GROUP BY ?cat
    ORDER BY DESC(?count)
    LIMIT 50
    """
    result = client.sparql(query)
    return result["results"]["bindings"]


def export_to_csv(output_path: str, client: SutraClient | None = None):
    """Export all data from SutraDB back to CSV."""
    if client is None:
        client = get_client()

    query = f"""
    SELECT ?item ?label ?domain ?p31Count ?categoryCount
    WHERE {{
        ?item <{SCHEMA}label> ?label .
        ?item <{SCHEMA}domain> ?domain .
        ?item <{SCHEMA}p31Count> ?p31Count .
        ?item <{SCHEMA}categoryCount> ?categoryCount .
    }}
    ORDER BY ?domain ?label
    """
    result = client.sparql(query)
    rows = []
    for b in result["results"]["bindings"]:
        rows.append({
            "qid": b["item"]["value"].rsplit("/", 1)[-1],
            "label": b["label"]["value"],
            "domain": b["domain"]["value"],
            "p31_count": int(b["p31Count"]["value"]),
            "category_count": int(b["categoryCount"]["value"]),
        })

    df = pd.DataFrame(rows)
    df.to_csv(output_path, index=False)
    return df
