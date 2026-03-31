# Wikidata Ontology Analysis (COSC 301)

Comparing Wikidata P31 (instance of) properties with English Wikipedia categories to assess how consistently different subject areas are categorized.

**Team:** Emma Leonhart, Evan Pasenau, Jordyn Campen

## Analytics Questions

1. Do Wikipedia categories line up with the Wikidata ontology?
2. Do they align more in certain domains (animals, films, cities, etc.)?
3. Are some categories of information easier to categorize than others?

## Project Structure

```
src/
  wikidata.py    - SPARQL queries against Wikidata
  wikipedia.py   - Wikipedia API category fetching
  etl.py         - Merge + clean both sources
  analysis.py    - Overlap and summary statistics
acquire.py       - Main data acquisition script
tests/           - Unit tests (pytest)
reports/         - Quarto report
data/            - Raw and processed CSV output
```

## Quick Start

```bash
pip install -r requirements.txt
python acquire.py 50         # fetch 50 items per domain
python -m pytest tests/ -v   # run tests
```

## Pipeline

1. **Acquire** — SPARQL fetches P31 items per domain; Wikipedia API fetches categories
2. **Clean/Merge** — Join on item, normalize, export CSV
3. **Analyze** — Compute P31-vs-category overlap per item and per domain
4. **Report** — Quarto document with R (ggplot2) visualizations

## Tools

- Python (mwclient, SPARQLWrapper, pandas, requests)
- SPARQL (Wikidata Query Service)
- R + ggplot2 (visualizations)
- Quarto (reporting)
