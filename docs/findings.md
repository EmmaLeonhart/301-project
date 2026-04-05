# Findings

## Dataset Summary

We analyzed **203 items** across **5 domains**, each with Wikidata P31 (instance of)
properties and English Wikipedia categories.

| Domain | Items | Avg P31 Types | Avg Wikipedia Categories |
|--------|-------|---------------|--------------------------|
| Films | 50 | 1.02 | 23.28 |
| Albums | 50 | 1.00 | 5.98 |
| Chemical Elements | 50 | 1.96 | 6.82 |
| Cities | 50 | 3.34 | 6.92 |
| Animals | 3 | 1.67 | 7.33 |

Note: The animals domain returned only 3 items due to SPARQL constraints (most
animals on Wikidata are typed as `Q16521 (taxon)` rather than `Q729 (animal)`).

## Substring Matching Results

The initial surface-level analysis (does the P31 label appear as a substring in any
Wikipedia category?) reveals stark domain-level differences:

| Domain | Mean Overlap | Median Overlap | Interpretation |
|--------|-------------|----------------|----------------|
| Films | 0.99 | 1.00 | Near-perfect alignment |
| Albums | 0.96 | 1.00 | Near-perfect alignment |
| Chemical Elements | 0.79 | 1.00 | High but imperfect |
| Cities | 0.04 | 0.00 | Very poor alignment |
| Animals | 0.00 | 0.00 | No alignment at all |

### Why the Divergence?

**High-overlap domains (films, albums):** These have simple, generic P31 types
(`"film"`, `"album"`) that Wikipedia editors also use in their category names
(`"2020 films"`, `"Rock albums"`). The vocabulary is shared because both systems
converge on the same common-language terms.

**Low-overlap domains (cities, animals):** The two systems use fundamentally different
vocabularies:

- **Cities:** Wikidata types like `"big city"`, `"municipality of Germany"`,
  `"statutory city"` are administrative/ontological terms. Wikipedia categories like
  `"Cities in North Rhine-Westphalia"` use geographic groupings. The word `"city"`
  appears in both, but Wikidata's more specific types (`"big city"`) don't substring-
  match against `"Cities in..."` because the matching is checked in both directions
  but these specific compound terms don't align.

- **Animals:** Wikidata uses `"Animalia"` and `"taxon"` — formal taxonomic terms that
  never appear in Wikipedia's categories (`"Mammals of Japan"`, `"Rodents of Europe"`).
  The classification systems are completely disjoint at the surface level.

## Answering the Analytics Questions

### Q1: Do Wikipedia categories line up with the Wikidata ontology?

**Partially.** Alignment ranges from 99% (films) to 0% (animals). The two systems
use fundamentally different classification strategies — Wikidata aims for formal
ontological precision, while Wikipedia categories serve as navigational and topical
groupings created by human editors.

### Q2: Do they align more in certain domains?

**Yes, dramatically.** Cultural/media domains (films, albums) where both systems
use everyday English terms show near-perfect alignment. Scientific domains (animals)
and geographic/administrative domains (cities) show poor alignment because they use
specialized vocabularies that don't overlap.

### Q3: Are some categories of information easier to categorize than others?

**Yes.** Domains with fewer, more generic P31 types align better. Films average
1.02 P31 values and match at 99%. Cities average 3.34 P31 values (more specific,
more diverse types) and match at only 4%. The more precise an ontological
classification, the less likely it maps to Wikipedia's informal category system.

## Limitations of Substring Matching

The substring approach answers "do they use the same words?" but not "do they mean
the same things?" For example:

- `"Animalia"` and `"Mammals of Japan"` are clearly related (mammals are animals),
  but share no substring
- `"big city"` and `"Cities in Germany"` are about the same concept but don't
  match because `"big city"` ≠ `"cities"`
- A chemical element typed as `"allotrope"` on Wikidata won't match Wikipedia's
  `"Chemical elements"` category, even though allotropes are forms of elements

This is why the ontology hop-distance analysis is the more meaningful metric: it
walks up both hierarchies to find where they converge semantically, not just
lexically.
