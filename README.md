# Wikidata Ontology vs Wikipedia Categories

**COSC 301 — Data Analytics**
Emma Leonhart, Evan Pasenau, Jordyn Campen

Comparing Wikidata's formal P31 (instance of) ontology with English Wikipedia's
crowd-sourced category system to measure how consistently different knowledge domains
are classified across the two platforms.

**[View the project site](https://emmaleonhart.github.io/301-project/)** | **[Download report (PDF)](https://emmaleonhart.github.io/301-project/report.pdf)**

## Quick Start

```bash
pip install -r requirements.txt
python acquire.py 50         # fetch 50 items per domain
python -m pytest tests/ -v   # run tests
```

## Analytics Questions

1. Do Wikipedia categories line up with the Wikidata ontology?
2. Do they align more in certain domains (animals, films, cities, etc.)?
3. Are some categories of information easier to categorize than others?

## How It Works

The pipeline fetches items from five domains (animals, films, cities, chemical
elements, albums), retrieves both their Wikidata P31 types and their Wikipedia
categories, then measures alignment using two methods:

- **Substring matching:** Does the P31 label appear in any Wikipedia category name?
- **Ontology hop distance:** How many hops up the P279 (subclass of) and parent
  category hierarchies before the two systems converge?

See [docs/methodology.md](docs/methodology.md) for the full methodology.

## Documentation

| Document | Description |
|----------|-------------|
| [docs/methodology.md](docs/methodology.md) | Data sources, analysis approaches, role of graph databases |
| [docs/findings.md](docs/findings.md) | Results, domain comparisons, answers to analytics questions |
| [docs/pipeline.md](docs/pipeline.md) | Pipeline architecture, GitHub Actions integration, SutraDB |
| [docs/github-actions.md](docs/github-actions.md) | What GitHub Actions is, runner environment, how our workflows connect |
| [SUMMARY.md](SUMMARY.md) | Project summary and status |

## Project Structure

```
acquire.py                  Main entry point
src/
  wikidata.py               SPARQL queries (P31 items + P279 hierarchy)
  wikipedia.py              Wikipedia API (categories + parent categories)
  etl.py                    Merge + clean both data sources
  analysis.py               Overlap metrics and hop distance
  sutradb_store.py          SutraDB graph database integration
data/processed/             Output CSVs (tracked in git)
tests/                      Unit tests (pytest)
reports/report.qmd          Quarto report (Python/matplotlib visualizations)
docs/index.html             GitHub Pages site
```

## Tools

- **Python** — pandas, SPARQLWrapper, requests (data pipeline)
- **SPARQL** — Wikidata Query Service (graph queries)
- **SutraDB** — Embeddable graph database for local RDF triple storage
- **Python + matplotlib** — Visualizations
- **Quarto** — Reproducible report generation (renders to PDF)
- **GitHub Actions** — CI and automated pipeline runs (data committed before report rendering to prevent data loss)
