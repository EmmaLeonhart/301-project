# 301-project

## Workflow Rules
- **Commit early and often.** Every meaningful change gets a commit with a clear message explaining *why*, not just what.
- **Do not enter planning-only modes.** All thinking must produce files and commits. If scope is unclear, create a `planning/` directory and write `.md` files there instead of using an internal planning mode.
- **Keep this file up to date.** As the project takes shape, record architectural decisions, conventions, and anything needed to work effectively in this repo.
- **Update README.md regularly.** It should always reflect the current state of the project for human readers.

## Testing
- **Write unit tests early.** As soon as there is testable logic, create a test file. Use `pytest` for Python projects or the appropriate test framework for the language in use.
- **Set up CI as soon as tests exist.** Create a `.github/workflows/ci.yml` GitHub Actions workflow that runs the test suite on push and pull request. Keep the workflow simple — install dependencies and run tests.
- **Keep tests passing.** Do not commit code that breaks existing tests. If a change requires updating tests, update them in the same commit.

## Project Description
Wikidata ontology analysis: comparing P31 (instance of) properties with English Wikipedia categories across domains (animals, films, cities, chemical elements, albums) to assess categorization consistency.

## Architecture and Conventions
- `src/wikidata.py` — SPARQL queries against Wikidata Query Service
- `src/wikipedia.py` — Wikipedia API category fetching via requests
- `src/etl.py` — Merges both data sources into a single DataFrame
- `src/analysis.py` — Overlap computation and domain summaries
- `acquire.py` — Main entry point: fetches data, runs analysis, saves CSVs to `data/processed/`
- `reports/report.qmd` — Quarto report with R (ggplot2) visualizations
- Domains configured in `src/wikidata.py:DOMAINS` dict
- All API calls include rate limiting (time.sleep) and User-Agent headers
- Data files (CSVs) are tracked in git for reproducibility

# currentDate
Today's date is 2026-03-31.
