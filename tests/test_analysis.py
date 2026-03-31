"""Tests for the analysis module — no network calls needed."""

import pandas as pd
from src.analysis import p31_category_overlap, domain_summary


def _sample_df():
    return pd.DataFrame([
        {
            "qid": "Q1",
            "label": "Test Animal",
            "enwiki_title": "Test_Animal",
            "domain": "animals",
            "p31_classes": "animal|mammal",
            "p31_qids": "Q729|Q7377",
            "wikipedia_categories": "Animals|Mammals|Endangered species",
            "p31_count": 2,
            "category_count": 3,
        },
        {
            "qid": "Q2",
            "label": "Test Film",
            "enwiki_title": "Test_Film",
            "domain": "films",
            "p31_classes": "film",
            "p31_qids": "Q11424",
            "wikipedia_categories": "2020 films|Drama films",
            "p31_count": 1,
            "category_count": 2,
        },
        {
            "qid": "Q3",
            "label": "Test City",
            "enwiki_title": "Test_City",
            "domain": "cities",
            "p31_classes": "city|big city",
            "p31_qids": "Q515|Q1549591",
            "wikipedia_categories": "Cities|Populated places",
            "p31_count": 2,
            "category_count": 2,
        },
    ])


def test_p31_category_overlap_adds_columns():
    df = _sample_df()
    result = p31_category_overlap(df)
    assert "overlap_count" in result.columns
    assert "overlap_ratio" in result.columns
    assert len(result) == 3


def test_p31_category_overlap_substring_matching():
    df = _sample_df()
    result = p31_category_overlap(df)
    # Q1: "animal" is substring of "Animals" (case-insensitive) -> match
    # "mammal" is substring of "Mammals" -> match
    q1 = result[result["qid"] == "Q1"].iloc[0]
    assert q1["overlap_count"] == 2

    # Q2: "film" is substring of "2020 films" and "Drama films" -> match
    q2 = result[result["qid"] == "Q2"].iloc[0]
    assert q2["overlap_count"] == 1
    assert q2["overlap_ratio"] == 1.0

    # Q3: "city" is NOT a substring of "cities" (different words), and
    # "big city" is not in "Cities" or "Populated places"
    q3 = result[result["qid"] == "Q3"].iloc[0]
    assert q3["overlap_count"] == 0


def test_p31_category_overlap_exact_match():
    df = pd.DataFrame([{
        "qid": "Q99",
        "label": "Exact",
        "enwiki_title": "Exact",
        "domain": "test",
        "p31_classes": "film|drama",
        "p31_qids": "Q1|Q2",
        "wikipedia_categories": "Film|Comedy",
        "p31_count": 2,
        "category_count": 2,
    }])
    result = p31_category_overlap(df)
    q = result.iloc[0]
    assert q["overlap_count"] == 1  # "film" matches "Film"
    assert q["overlap_ratio"] == 0.5


def test_domain_summary():
    df = _sample_df()
    result = domain_summary(df)
    assert len(result) == 3
    assert set(result["domain"]) == {"animals", "films", "cities"}
    assert all(result["item_count"] == 1)


def test_empty_p31():
    df = pd.DataFrame([{
        "qid": "Q0",
        "label": "Empty",
        "enwiki_title": "Empty",
        "domain": "test",
        "p31_classes": "",
        "p31_qids": "",
        "wikipedia_categories": "Something",
        "p31_count": 0,
        "category_count": 1,
    }])
    result = p31_category_overlap(df)
    assert result.iloc[0]["overlap_ratio"] == 0.0
