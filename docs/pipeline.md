# Data Pipeline

## Design Philosophy

The entire pipeline is designed to run end-to-end in GitHub Actions. There is no
manual step, no local server to configure, and no state that lives outside the
repository. Every run produces the same outputs from the same code — the only
variable is the live state of Wikidata and Wikipedia at query time.

This is intentional. The pipeline is a cron job that could run daily, producing an
updated snapshot each time. The generated report (PDF) is committed to the repository
and tracked in git, so every historical version is recoverable.

## Stages

### 1. Acquire (`acquire.py`)

Entry point. Calls the ETL module to fetch and merge data, then runs analysis.

```bash
python acquire.py 50    # 50 items per domain
```

### 2. Fetch Wikidata (`src/wikidata.py`)

For each domain (animals, films, cities, chemical elements, albums):

1. SPARQL query fetches items that are `P31 (instance of)` the domain's target class,
   filtered to items with an English Wikipedia sitelink
2. For each item, a second SPARQL query fetches all its P31 values
3. For hop-distance analysis, P279 (subclass of) ancestors are traversed upward

All queries include a `User-Agent` header and `time.sleep()` delays.

**SPARQL example — fetch films:**
```sparql
SELECT ?item ?itemLabel ?sitelink WHERE {
  ?item wdt:P31 wd:Q11424 .
  ?sitelink schema:about ?item ;
           schema:isPartOf <https://en.wikipedia.org/> ;
           schema:name ?articleTitle .
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
LIMIT 50
```

### 3. Fetch Wikipedia Categories (`src/wikipedia.py`)

For each item's English Wikipedia article, the Wikipedia API returns non-hidden
categories. For hop-distance analysis, parent categories are fetched recursively.

**API call example:**
```
GET /w/api.php?action=query&titles=Inception_(film)&prop=categories&clshow=!hidden&format=json
```

### 4. Merge and Clean (`src/etl.py`)

Joins Wikidata P31 data with Wikipedia categories into a single pandas DataFrame.
P31 class labels and Wikipedia categories are stored as pipe-delimited strings.
Outputs `data/processed/ontology_comparison.csv`.

### 5. Analyze (`src/analysis.py`)

Two analysis methods:

- **Substring overlap:** What fraction of P31 labels appear in Wikipedia category
  names? (Surface-level lexical comparison)
- **Hop distance:** How many hops up each hierarchy before they converge?
  (Semantic/structural comparison)

Outputs `data/processed/domain_summary.csv`.

### 6. Report

- **GitHub Pages** (`docs/index.html`): Static site with findings and CSS charts
- **Quarto** (`reports/report.qmd`): R/ggplot2 visualizations, renders to PDF

## Running in GitHub Actions

The pipeline requires only Python and R (for Quarto). No database server, no Docker,
no external services beyond the Wikidata and Wikipedia APIs (which are public).

```yaml
# Simplified workflow
- uses: actions/setup-python@v5
- run: pip install -r requirements.txt
- run: python acquire.py 50
- run: quarto render reports/report.qmd --to pdf
- run: git add data/ reports/ && git commit -m "Update data" && git push
```

The generated PDF is committed to the repository. Since it's tracked in git, every
previous version is preserved in history — the latest commit always has the most
recent run.

## Graph Database Considerations

### What We Use: Wikidata's SPARQL Endpoint

Wikidata itself *is* a graph database. Our SPARQL queries against the Wikidata Query
Service are already graph database queries — we're traversing P31 and P279 edges in
a live triple store containing over 100 million items.

### What SutraDB Would Add

SutraDB is an embeddable graph database (no server process — runs in-process like
SQLite). It would allow us to:

1. Load both the Wikidata ontology fragment and Wikipedia category tree locally
2. Run SPARQL joins across both graphs without repeated API calls
3. Cache the combined graph between pipeline runs

This is most valuable for the hop-distance analysis, where we traverse both
hierarchies simultaneously. Without a local graph store, each hierarchy traversal
requires live API calls.

### Why SutraDB Works in CI

Unlike PostgreSQL or Neo4j, SutraDB requires no daemon process. It runs embedded
in the Python process, storing data in a local file. This makes it compatible with
GitHub Actions out of the box — `pip install sutradb` and it works, same as SQLite.

```python
from sutradb import SutraClient
client = SutraClient("./local.db")  # file-based, no server
client.insert_triples(rdf_data)
results = client.sparql("SELECT ...")
```

### Current Status

The SutraDB integration code exists (`src/sutradb_store.py`) but the pipeline
currently runs against live APIs directly. SutraDB would become more important if:
- We increase sample sizes (more API calls to cache)
- We add more complex graph queries (multi-hop path finding)
- We want offline/reproducible analysis (fixed snapshot instead of live data)
