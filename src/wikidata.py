"""Fetch P31 (instance of) properties from Wikidata via SPARQL."""

import time
from SPARQLWrapper import SPARQLWrapper, JSON


WIKIDATA_SPARQL = "https://query.wikidata.org/sparql"
USER_AGENT = "COSC301-OntologyAnalysis/1.0 (university project)"
MAX_RETRIES = 4

# Domains to compare — each maps a human label to a Wikidata class QID.
# We fetch items that are P31 (instance of) these classes.
DOMAINS = {
    "animals": {
        "Q729": "animal",
    },
    "films": {
        "Q11424": "film",
    },
    "cities": {
        "Q515": "city",
    },
    "chemical_elements": {
        "Q11344": "chemical element",
    },
    "albums": {
        "Q482994": "album",
    },
}


def _sparql_endpoint():
    sparql = SPARQLWrapper(WIKIDATA_SPARQL)
    sparql.addCustomHttpHeader("User-Agent", USER_AGENT)
    sparql.setReturnFormat(JSON)
    return sparql


def _query_with_retry(sparql, retries: int = MAX_RETRIES):
    """Execute a SPARQL query with exponential backoff on 429 errors."""
    from urllib.error import HTTPError
    for attempt in range(retries):
        try:
            return sparql.query().convert()
        except HTTPError as e:
            if e.code == 429 and attempt < retries - 1:
                wait = 2 ** (attempt + 1)
                print(f"    Rate limited (429), retrying in {wait}s...")
                time.sleep(wait)
            else:
                raise


def fetch_items_for_class(class_qid: str, limit: int = 500) -> list[dict]:
    """Return items that are P31 (instance of) the given class.

    Each result dict has keys: item (QID), itemLabel, sitelink (enwiki title).
    Only items with an English Wikipedia article are returned.
    """
    query = f"""
    SELECT ?item ?itemLabel ?sitelink WHERE {{
      ?item wdt:P31 wd:{class_qid} .
      ?sitelink schema:about ?item ;
               schema:isPartOf <https://en.wikipedia.org/> ;
               schema:name ?articleTitle .
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
    }}
    LIMIT {limit}
    """
    sparql = _sparql_endpoint()
    sparql.setQuery(query)
    results = _query_with_retry(sparql)

    items = []
    for row in results["results"]["bindings"]:
        qid = row["item"]["value"].rsplit("/", 1)[-1]
        label = row["itemLabel"]["value"]
        sitelink = row["sitelink"]["value"].rsplit("/wiki/", 1)[-1]
        items.append({"qid": qid, "label": label, "enwiki_title": sitelink})
    return items


def fetch_p31_values(qid: str) -> list[dict]:
    """Return all P31 (instance of) values for a given item."""
    query = f"""
    SELECT ?class ?classLabel WHERE {{
      wd:{qid} wdt:P31 ?class .
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
    }}
    """
    sparql = _sparql_endpoint()
    sparql.setQuery(query)
    results = _query_with_retry(sparql)

    classes = []
    for row in results["results"]["bindings"]:
        class_qid = row["class"]["value"].rsplit("/", 1)[-1]
        class_label = row["classLabel"]["value"]
        classes.append({"qid": class_qid, "label": class_label})
    return classes


def fetch_p279_parents(qids: list[str], delay: float = 1.0) -> dict[str, list[dict]]:
    """Fetch P279 (subclass of) parents for a batch of QIDs.

    Returns dict mapping each input QID to its list of parent classes:
        {'Q515': [{'qid': 'Q486972', 'label': 'human settlement'}, ...]}
    """
    if not qids:
        return {}

    values_clause = " ".join(f"wd:{qid}" for qid in qids)
    query = f"""
    SELECT ?item ?parent ?parentLabel WHERE {{
      VALUES ?item {{ {values_clause} }}
      ?item wdt:P279 ?parent .
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
    }}
    """
    sparql = _sparql_endpoint()
    sparql.setQuery(query)
    time.sleep(delay)
    results = _query_with_retry(sparql)

    parents: dict[str, list[dict]] = {qid: [] for qid in qids}
    for row in results["results"]["bindings"]:
        item_qid = row["item"]["value"].rsplit("/", 1)[-1]
        parent_qid = row["parent"]["value"].rsplit("/", 1)[-1]
        parent_label = row["parentLabel"]["value"]
        if item_qid in parents:
            parents[item_qid].append({"qid": parent_qid, "label": parent_label})
    return parents


def fetch_p279_chain(start_qids: list[str], max_depth: int = 5, delay: float = 2.0) -> dict[int, list[dict]]:
    """BFS up the P279 (subclass of) hierarchy from starting QIDs.

    Returns {depth: [{'qid': ..., 'label': ...}]} where depth 0 is not included
    (that's the starting P31 values themselves).
    """
    visited = set(start_qids)
    current_level = list(start_qids)
    result = {}

    for depth in range(1, max_depth + 1):
        if not current_level:
            break

        # Batch into groups of 50 to avoid query limits
        all_parents = []
        for i in range(0, len(current_level), 50):
            batch = current_level[i:i + 50]
            parents = fetch_p279_parents(batch, delay=delay)
            for parent_list in parents.values():
                for p in parent_list:
                    if p["qid"] not in visited:
                        visited.add(p["qid"])
                        all_parents.append(p)

        if all_parents:
            result[depth] = all_parents
        current_level = [p["qid"] for p in all_parents]

    return result


def fetch_domain(domain_name: str, limit: int = 500, delay: float = 1.0) -> list[dict]:
    """Fetch items + their full P31 values for a domain.

    Returns list of dicts with keys: qid, label, enwiki_title, p31_classes, domain.
    """
    if domain_name not in DOMAINS:
        raise ValueError(f"Unknown domain: {domain_name}. Choose from {list(DOMAINS)}")

    all_items = []
    for class_qid, class_label in DOMAINS[domain_name].items():
        items = fetch_items_for_class(class_qid, limit=limit)
        for item in items:
            time.sleep(delay)
            p31 = fetch_p31_values(item["qid"])
            item["p31_classes"] = p31
            item["domain"] = domain_name
            all_items.append(item)
    return all_items
