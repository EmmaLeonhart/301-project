"""Tests for the analysis module — no network calls needed."""

import pandas as pd
from src.analysis import p910_category_overlap, domain_summary, compute_category_depth


def _sample_df():
    return pd.DataFrame([
        {
            "qid": "Q1",
            "label": "Test Animal",
            "enwiki_title": "Test_Animal",
            "domain": "animals",
            "p31_classes": "animal|mammal",
            "p31_qids": "Q729|Q7377",
            "p910_categories": "Animals|Mammals",
            "p910_count": 2,
            "wikipedia_categories": "Animals|Mammals|Endangered species",
            "p31_count": 2,
            "category_count": 3,
            "p910_depth": 0,
            "p910_matched_category": "Animals",
        },
        {
            "qid": "Q2",
            "label": "Test Film",
            "enwiki_title": "Test_Film",
            "domain": "films",
            "p31_classes": "film",
            "p31_qids": "Q11424",
            "p910_categories": "Films",
            "p910_count": 1,
            "wikipedia_categories": "2020 films|Drama films",
            "p31_count": 1,
            "category_count": 2,
            "p910_depth": -1,
            "p910_matched_category": "",
        },
        {
            "qid": "Q3",
            "label": "Test City",
            "enwiki_title": "Test_City",
            "domain": "cities",
            "p31_classes": "city|big city",
            "p31_qids": "Q515|Q1549591",
            "p910_categories": "Cities",
            "p910_count": 1,
            "wikipedia_categories": "Cities|Populated places",
            "p31_count": 2,
            "category_count": 2,
            "p910_depth": 0,
            "p910_matched_category": "Cities",
        },
    ])


def test_p910_overlap_adds_columns():
    df = _sample_df()
    result = p910_category_overlap(df)
    assert "overlap_count" in result.columns
    assert "overlap_ratio" in result.columns
    assert "matched_categories" in result.columns
    assert len(result) == 3


def test_p910_overlap_exact_match():
    """P910 categories that are in Wikipedia categories should match."""
    df = _sample_df()
    result = p910_category_overlap(df)

    # Q1: P910 gives "Animals" and "Mammals", both in Wikipedia categories
    q1 = result[result["qid"] == "Q1"].iloc[0]
    assert q1["overlap_count"] == 2
    assert q1["overlap_ratio"] == 1.0

    # Q2: P910 gives "Films", but item has "2020 films" and "Drama films" — no exact match
    q2 = result[result["qid"] == "Q2"].iloc[0]
    assert q2["overlap_count"] == 0
    assert q2["overlap_ratio"] == 0.0

    # Q3: P910 gives "Cities", which is in Wikipedia categories
    q3 = result[result["qid"] == "Q3"].iloc[0]
    assert q3["overlap_count"] == 1
    assert q3["overlap_ratio"] == 1.0


def test_domain_summary():
    df = _sample_df()
    result = domain_summary(df)
    assert len(result) == 3
    assert set(result["domain"]) == {"animals", "films", "cities"}
    assert all(result["item_count"] == 1)


def test_empty_p910():
    df = pd.DataFrame([{
        "qid": "Q0",
        "label": "Empty",
        "enwiki_title": "Empty",
        "domain": "test",
        "p31_classes": "something",
        "p31_qids": "Q1",
        "p910_categories": "",
        "p910_count": 0,
        "wikipedia_categories": "Something",
        "p31_count": 1,
        "category_count": 1,
        "p910_depth": -1,
        "p910_matched_category": "",
    }])
    result = p910_category_overlap(df)
    assert result.iloc[0]["overlap_ratio"] == 0.0


# --- Category depth tests ---

def test_category_depth_direct_match():
    """P910 category found at depth 0 (direct Wikipedia category)."""
    p910 = {"Films"}
    wp = {0: ["Films", "2020 films"]}
    result = compute_category_depth(p910, wp)
    assert result["min_depth"] == 0
    assert result["matched_category"] == "Films"


def test_category_depth_parent_match():
    """P910 category found in parent categories (depth 1)."""
    p910 = {"Films"}
    wp = {0: ["2020 films", "Drama films"], 1: ["Films", "Films by year"]}
    result = compute_category_depth(p910, wp)
    assert result["min_depth"] == 1
    assert result["matched_category"] == "Films"


def test_category_depth_deep_match():
    """P910 category found at depth 2."""
    p910 = {"Animals"}
    wp = {0: ["Mammals of Japan"], 1: ["Mammals by country"], 2: ["Animals", "Mammals"]}
    result = compute_category_depth(p910, wp)
    assert result["min_depth"] == 2
    assert result["matched_category"] == "Animals"


def test_category_depth_no_match():
    """P910 category not found anywhere in the hierarchy."""
    p910 = {"Chemical elements"}
    wp = {0: ["Rodents of Europe"], 1: ["Rodents"]}
    result = compute_category_depth(p910, wp)
    assert result["min_depth"] == -1
    assert result["matched_category"] == ""


def test_category_depth_empty():
    """Empty inputs."""
    result = compute_category_depth(set(), {})
    assert result["min_depth"] == -1

    result = compute_category_depth({"Films"}, {})
    assert result["min_depth"] == -1
