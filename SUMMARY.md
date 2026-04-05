# Project Summary — Wikidata Ontology vs Wikipedia Categories

**Course:** COSC 301 — Data Analytics
**Team:** Emma Leonhart, Evan Pasenau, Jordyn Campen

## What We Built

A Python data pipeline that compares how Wikidata and English Wikipedia categorize
the same entities. The core question: does Wikidata's formal ontology (P31 "instance
of" properties) line up with Wikipedia's crowd-sourced category system?

We sampled five domains — **animals, films, cities, chemical elements, and albums** —
fetching up to 50 items per domain from Wikidata, then pulling each item's Wikipedia
categories via the API.

## Pipeline Architecture

| Stage | File(s) | What it does |
|-------|---------|--------------|
| **Acquire** | `src/wikidata.py`, `src/wikipedia.py` | SPARQL queries fetch P31 items + P279 hierarchy; Wikipedia API fetches categories + parent categories |
| **Merge & Clean** | `src/etl.py` | Joins both data sources into a single pandas DataFrame, normalizes, exports CSV |
| **Analyze** | `src/analysis.py` | Substring overlap and ontology hop distance computation |
| **Store** | `src/sutradb_store.py` | SutraDB graph database for local RDF triple storage and SPARQL |
| **Report** | `docs/index.html`, `reports/report.qmd` | GitHub Pages site; Quarto report with R/ggplot2 visualizations |
| **Entry point** | `acquire.py` | Runs the full pipeline end-to-end |

## What We Did

1. **Built the data pipeline** — SPARQL queries against Wikidata Query Service,
   Wikipedia API calls with rate limiting and proper User-Agent headers, pandas
   merge/clean step. Designed to run fully automated in GitHub Actions.

2. **Acquired data for 5 domains** — 203 total items (50 each for films, cities,
   chemical elements, albums; only 3 for animals due to SPARQL query constraints).

3. **Computed overlap metrics** — Two analysis approaches:
   - Substring matching: do P31 labels appear in Wikipedia category names?
   - Ontology hop distance: how many hops up the P279/category hierarchies before
     the two systems converge?

4. **Wrote unit tests** — 5 tests in `tests/test_analysis.py` covering overlap
   computation, substring matching, domain summary, and edge cases.

5. **Created a GitHub Pages site** (`docs/index.html`) — Project website with
   methodology, pipeline documentation, findings, and CSS charts.

6. **Created a Quarto report** (`reports/report.qmd`) — R/ggplot2 visualizations
   (bar chart, scatter plot, box plot), renders to PDF.

7. **SutraDB integration** (`src/sutradb_store.py`) — Code for loading data as RDF
   triples into SutraDB, an embeddable graph database that works like SQLite for
   graph data. Supports SPARQL queries against the combined Wikidata + Wikipedia
   hierarchy data without requiring a running server.

## Key Findings

| Domain | Items | Mean Overlap | Median Overlap |
|--------|-------|-------------|----------------|
| Films | 50 | 0.99 | 1.00 |
| Albums | 50 | 0.96 | 1.00 |
| Chemical Elements | 50 | 0.79 | 1.00 |
| Cities | 50 | 0.04 | 0.00 |
| Animals | 3 | 0.00 | 0.00 |

- **Films and albums** have near-perfect alignment — simple P31 types map directly
  to Wikipedia naming conventions.
- **Cities** show poor alignment — Wikidata uses fine-grained administrative types
  that diverge from Wikipedia's geographic categories.
- **Animals** have zero surface overlap — Wikidata's scientific terms ("Animalia",
  "taxon") never appear in Wikipedia's common-language categories ("Mammals of
  Japan"). The hop-distance analysis reveals whether they converge higher up the
  hierarchy.
- **Domains with fewer, more generic P31 types align better.** Wikipedia favors
  human-readable topic groupings over formal ontological classification.

## Tools and Technologies

- **Python** — pandas, SPARQLWrapper, requests (data pipeline)
- **SPARQL** — Wikidata Query Service (querying a live graph database)
- **SutraDB** — Embeddable RDF graph database (local storage + SPARQL)
- **R + ggplot2** — Visualizations
- **Quarto** — Reproducible report generation (PDF output)
- **GitHub Pages** — Project website
- **GitHub Actions** — CI + automated pipeline runs
- **pytest** — Unit testing
