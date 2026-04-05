# Methodology

## Overview

This project compares Wikidata's formal ontology (P31 "instance of" properties) with
English Wikipedia's crowd-sourced category system to assess categorization consistency
across different knowledge domains.

## Data Sources

### Wikidata (Structured Ontology)

Wikidata assigns machine-readable properties to every entity. The property we focus on
is **P31 (instance of)**, which declares what kind of thing an entity is. For example,
the entity for *Inception* (Q25188) has `P31 = Q11424 (film)`.

These P31 values form part of a larger ontology. Each class can have **P279 (subclass
of)** relationships pointing to broader classes. For example:

```
Q11424 (film)
  └─ P279 → Q2431196 (audiovisual work)
       └─ P279 → Q17537576 (creative work)
            └─ P279 → Q386724 (work)
```

This creates a directed acyclic graph (DAG) of types that can be traversed upward to
find increasingly general classifications.

We query Wikidata via SPARQL against the [Wikidata Query Service](https://query.wikidata.org/).

### English Wikipedia (Crowd-Sourced Categories)

Wikipedia editors assign articles to categories by adding `[[Category:...]]` tags.
These categories also form a hierarchy — each category can have parent categories,
creating a DAG of topics. For example:

```
"Inception (film)" is in:
  ├─ "2010 science fiction action films"
  │    └─ "2010s science fiction action films"
  │         └─ "Science fiction action films"
  │              └─ "Science fiction films by genre"
  └─ "Films directed by Christopher Nolan"
       └─ "Christopher Nolan"
```

We query categories via the [Wikipedia API](https://en.wikipedia.org/w/api.php)
(`prop=categories`).

## Domains Sampled

We selected five domains representing different kinds of knowledge:

| Domain | Wikidata Class | QID | Why |
|--------|---------------|-----|-----|
| Animals | animal | Q729 | Scientific/taxonomic domain |
| Films | film | Q11424 | Pop culture / media |
| Cities | city | Q515 | Geographic / administrative |
| Chemical Elements | chemical element | Q11344 | Hard science |
| Albums | album | Q482994 | Pop culture / media |

For each domain, we fetch up to 50 items that are `P31` (instance of) that class and
also have an English Wikipedia article.

## Analysis: Two Approaches

### Approach 1: Substring Matching (Implemented)

The initial analysis uses a simple heuristic: for each item, check whether any P31
class label appears as a substring in any of its Wikipedia category names.

For example, the P31 label `"film"` matches the Wikipedia category `"2020 films"`
via case-insensitive substring containment.

```
overlap_ratio = matched_p31_labels / total_p31_labels
```

This is a **surface-level comparison** that only works when the two systems happen to
use the same word. It correctly identifies obvious alignments (films, albums) but
cannot detect semantic equivalences (`"Animalia"` vs `"Mammals of Japan"` — clearly
related, but no shared substring).

### Approach 2: Ontology Hop Distance (The Real Analysis)

The more meaningful analysis walks **up both hierarchies** and measures how many hops
it takes before they converge:

1. **Wikidata side:** Starting from an item's P31 values, follow P279 (subclass of)
   links upward through the class hierarchy.
2. **Wikipedia side:** Starting from an item's direct categories, follow parent
   category links upward through the category tree.
3. **Convergence:** At each level, check if any Wikidata ancestor label matches any
   Wikipedia ancestor category (via substring). The total number of hops
   (Wikidata hops + Wikipedia hops) to first match is the **hop distance**.

A hop distance of **0** means the P31 label directly appears in a Wikipedia category
(same as substring matching). A hop distance of **3** means you need to go up 3 total
levels across the two hierarchies before finding common ground. A hop distance of
**-1** means no convergence was found within the search depth.

This approach captures what substring matching misses: `"Animalia"` might not match
any Wikipedia category, but its P279 ancestor `"organism"` might match the Wikipedia
parent category `"Organisms by habitat"` after a few hops.

**Why this matters:** The hop distance is a much more informative metric than binary
match/no-match. It tells us *how far apart* the two classification systems are, not
just whether they happen to share vocabulary.

## Role of Graph Databases

### Why a Graph Database Makes Sense

Both Wikidata's ontology (P31 → P279 chains) and Wikipedia's category tree are
**directed acyclic graphs**. Traversing them — finding ancestors, computing shortest
paths, detecting convergence — is fundamentally a graph problem.

While SPARQL property paths can handle the Wikidata side (the Wikidata Query Service
supports `wdt:P279*` for transitive closure), the Wikipedia category tree has no
SPARQL endpoint. Combining both hierarchies for hop-distance analysis requires either:

- Iterative API calls with local caching (what we do during acquisition)
- Loading both graphs into a local graph database for efficient traversal

### SutraDB

[SutraDB](https://sutradb.com/) is a lightweight, embeddable graph database — often
described as "the SQLite of graph databases." It stores data as RDF triples and
supports SPARQL queries, making it a natural fit for ontology data.

In our pipeline, SutraDB could serve as the local store where both hierarchies are
loaded as RDF triples, enabling efficient SPARQL queries across the combined graph
without repeated API calls. It runs embedded (no server required), which means it
works in CI environments like GitHub Actions, similar to how SQLite works for
relational data.

**Current status:** We wrote the SutraDB integration code (`src/sutradb_store.py`,
`load_sutradb.py`) that loads our data as RDF triples and supports SPARQL queries.
However, the hop-distance analysis currently runs against the live APIs directly
rather than through SutraDB. The SutraDB layer exists as infrastructure for more
complex graph queries if needed.

## Pipeline

```
┌─────────────────┐     ┌─────────────────┐
│  Wikidata SPARQL │     │  Wikipedia API   │
│  (P31 + P279)   │     │  (categories +   │
│                  │     │   parent cats)   │
└────────┬────────┘     └────────┬────────┘
         │                       │
         └───────────┬───────────┘
                     │
              ┌──────▼──────┐
              │   ETL.py    │
              │  merge +    │
              │  clean      │
              └──────┬──────┘
                     │
              ┌──────▼──────┐
              │ analysis.py │
              │  overlap +  │
              │  hop dist   │
              └──────┬──────┘
                     │
         ┌───────────┼───────────┐
         │           │           │
    ┌────▼────┐ ┌────▼────┐ ┌───▼────┐
    │  CSVs   │ │  Quarto │ │ GitHub │
    │         │ │  Report │ │ Pages  │
    └─────────┘ └─────────┘ └────────┘
```

All steps run via `python acquire.py` and can be automated with GitHub Actions.

## Rate Limiting and Ethics

- All API requests include a descriptive `User-Agent` header
- `time.sleep()` delays between requests to respect rate limits
- Only English Wikipedia is queried (acknowledged Anglophone bias)
- Data reflects a snapshot in time; both Wikidata and Wikipedia change constantly
