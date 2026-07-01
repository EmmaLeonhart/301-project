# 301-project

## Skills

Workflow behaviors live as skills in `.claude/skills/` (auto-discovered by Claude Code):
`emergency-stop`, `cron-is-local`, `autonomous-loop`, `queue-driven-workflow`,
`writing-style`, `cleanvibe-update-check`. They are vendored into this repo and kept
current by the `cleanvibe-update-check` skill.

- **Last cleanvibe update check:** `never`
- **Updates source:** <https://cleanvibe.emmaleonhart.com/updates.md>


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

## Long command series run in strict order
When Emma gives a long series of commands, treat it as a long series of commands to be
executed in relatively STRICT ORDER, one after another, EVEN IF the order seems not to
make sense or seems inefficient. The sequencing is intentional — she organizes the steps
so states change in the order she wants. Do not reorder, merge, or skip steps.
