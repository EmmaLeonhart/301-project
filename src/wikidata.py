"""Fetch P31 (instance of) properties from Wikidata via SPARQL."""

import time
from SPARQLWrapper import SPARQLWrapper, JSON


WIKIDATA_SPARQL = "https://query.wikidata.org/sparql"
USER_AGENT = "COSC301-OntologyAnalysis/1.0 (university project)"

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
    results = sparql.query().convert()

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
    results = sparql.query().convert()

    classes = []
    for row in results["results"]["bindings"]:
        class_qid = row["class"]["value"].rsplit("/", 1)[-1]
        class_label = row["classLabel"]["value"]
        classes.append({"qid": class_qid, "label": class_label})
    return classes


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
