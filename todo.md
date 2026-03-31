# TODO — Wikidata Ontology Analysis (COSC 301)

## Data Acquisition
- [ ] Increase sample size beyond 50 items per domain
- [ ] Fix animals domain — only 3 items returned (SPARQL query may need broadening, e.g. include subclasses)
- [ ] Add more domains to compare (e.g. books, songs, countries, universities, sports teams)
- [ ] Cache raw API responses locally to avoid re-fetching during development
- [ ] Add exponential backoff for API rate limits (currently just fixed sleep)

## Analysis
- [ ] Improve matching beyond simple substring (e.g. stemming: "city"/"cities", "animal"/"animals")
- [ ] Analyze which specific P31 classes never appear in Wikipedia categories and vice versa
- [ ] Compute per-item detail: which P31 labels matched, which didn't, and what Wikipedia categories were unmatched
- [ ] Statistical significance testing across domains (are differences meaningful or just sample noise?)
- [ ] Look at P31 depth — do items with more P31 values have more or fewer category matches?

## SutraDB Integration
- [ ] Set up SutraDB graph database
- [ ] Load cleaned data into SutraDB
- [ ] Export from SutraDB to CSV for R analysis
- [ ] Document SutraDB schema and queries

## Visualization / R
- [ ] Create ggplot2 bar chart: overlap ratio by domain
- [ ] Create scatter plot: P31 count vs category count, colored by domain
- [ ] Create box plot: overlap distribution per domain
- [ ] Create heatmap: which P31 classes match which Wikipedia category patterns
- [ ] Make sure all plots render correctly in Quarto

## Quarto Report
- [ ] Write introduction and methodology sections
- [ ] Write findings section interpreting the overlap data
- [ ] Write ethics/limitations section (cultural bias, API limits, snapshot-in-time)
- [ ] Add inline Python/R code blocks for reproducible numbers
- [ ] Final formatting and proofreading

## Infrastructure
- [ ] Verify CI passes on GitHub Actions
- [ ] Add integration tests (small live queries) gated behind a flag
- [ ] Add a `--domain` flag to acquire.py for selective fetching
