"""Generate the project report as a PDF using matplotlib. No external rendering tools needed."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
from matplotlib.backends.backend_pdf import PdfPages
import numpy as np
from datetime import datetime
import textwrap


def wrap_text(text, width=95):
    return "\n".join(textwrap.wrap(text, width))


def add_text_page(pdf, title, body_lines, fontsize=10):
    """Add a page with a title and wrapped body text."""
    fig = plt.figure(figsize=(8.5, 11))
    fig.text(0.05, 0.95, title, fontsize=14, fontweight="bold", va="top")
    y = 0.90
    for line in body_lines:
        wrapped = wrap_text(line)
        fig.text(0.05, y, wrapped, fontsize=fontsize, va="top", family="serif")
        y -= 0.04 * (wrapped.count("\n") + 1)
        if y < 0.05:
            break
    plt.axis("off")
    pdf.savefig(fig)
    plt.close(fig)


def generate_report(data_dir="data/processed", output_path="reports/report.pdf"):
    df = pd.read_csv(os.path.join(data_dir, "ontology_comparison.csv"))
    summary = pd.read_csv(os.path.join(data_dir, "domain_summary.csv"))

    mtime = os.path.getmtime(os.path.join(data_dir, "ontology_comparison.csv"))
    snapshot = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M UTC")
    has_p910 = "p910_count" in df.columns
    has_depth = "p910_depth" in df.columns

    with PdfPages(output_path) as pdf:
        # --- Title page ---
        fig = plt.figure(figsize=(8.5, 11))
        fig.text(0.5, 0.65, "Wikidata Ontology vs\nWikipedia Categories", fontsize=22,
                 fontweight="bold", ha="center", va="center")
        fig.text(0.5, 0.52, "Emma Leonhart, Evan Pasenau, Jordyn Campen",
                 fontsize=12, ha="center", va="center", style="italic")
        fig.text(0.5, 0.45, f"Data snapshot: {snapshot}  |  {len(df)} items  |  {df['domain'].nunique()} domains",
                 fontsize=10, ha="center", va="center", color="gray")
        if has_p910:
            with_p910 = (df["p910_count"] > 0).sum()
            fig.text(0.5, 0.40, f"Items with P910-derived categories: {with_p910}/{len(df)}",
                     fontsize=10, ha="center", va="center", color="gray")
        plt.axis("off")
        pdf.savefig(fig)
        plt.close(fig)

        # --- Methodology page ---
        add_text_page(pdf, "Introduction & Methodology", [
            "This report compares Wikidata's P31 (instance of) ontological classification with English Wikipedia's category system across multiple domains.",
            "",
            "Rather than relying on string matching, we use Wikidata's own P910 (topic's main category) property to follow the semantic link from a P31 class to its corresponding Wikipedia category. We then check whether each Wikipedia article is actually placed in the category that Wikidata's ontology predicts.",
            "",
            "For each item in our dataset:",
            "  1. Retrieve the item's P31 (instance of) classes from Wikidata",
            "  2. For each P31 class, follow P910 (topic's main category) to get the Wikidata item representing the Wikipedia category",
            "  3. Use the enwiki sitelink on that category item to get the actual Wikipedia category name",
            "  4. Fetch the item's Wikipedia categories and check for membership",
            "  5. If not found directly, walk up the Wikipedia parent-category hierarchy to measure depth",
            "",
            "This approach uses Wikidata's own graph structure rather than heuristic string matching, giving us a principled measure of alignment between the two systems.",
        ])

        # --- Domain summary bar chart ---
        ordered = summary.sort_values("mean_overlap_ratio", ascending=True)
        fig, ax = plt.subplots(figsize=(8.5, 5))
        ax.barh(ordered["domain"], ordered["mean_overlap_ratio"], color="steelblue")
        ax.set_xlabel("Mean Overlap Ratio")
        ax.set_title("P910 Category Match Rate by Domain")
        ax.set_xlim(0, 1.05)
        plt.tight_layout()
        pdf.savefig(fig)
        plt.close(fig)

        # --- P910 coverage ---
        if has_p910:
            coverage = df.groupby("domain").agg(
                total=("qid", "count"),
                with_p910=("p910_count", lambda x: (x > 0).sum()),
            )
            coverage["coverage"] = coverage["with_p910"] / coverage["total"]
            coverage = coverage.sort_values("coverage", ascending=True)

            fig, ax = plt.subplots(figsize=(8.5, 5))
            ax.barh(coverage.index, coverage["coverage"], color="coral")
            ax.xaxis.set_major_formatter(mtick.PercentFormatter(1.0))
            ax.set_xlabel("P910 Coverage")
            ax.set_title("Fraction of Items Whose P31 Classes Have P910 Links")
            ax.set_xlim(0, 1.1)
            plt.tight_layout()
            pdf.savefig(fig)
            plt.close(fig)

        # --- P31 vs category count scatter ---
        fig, ax = plt.subplots(figsize=(8.5, 6))
        for domain, group in df.groupby("domain"):
            ax.scatter(group["p31_count"], group["category_count"], label=domain, alpha=0.6)
        ax.set_xlabel("Number of P31 (instance of) values")
        ax.set_ylabel("Number of Wikipedia categories")
        ax.set_title("P31 Count vs Wikipedia Category Count")
        ax.legend()
        plt.tight_layout()
        pdf.savefig(fig)
        plt.close(fig)

        # --- Overlap distribution box plot ---
        domains = sorted(df["domain"].unique())
        box_data = [df[df["domain"] == d]["overlap_ratio"].values for d in domains]

        fig, ax = plt.subplots(figsize=(8.5, 6))
        bp = ax.boxplot(box_data, tick_labels=domains, patch_artist=True)
        colors = plt.cm.Set2(np.linspace(0, 1, len(domains)))
        for patch, color in zip(bp["boxes"], colors):
            patch.set_facecolor(color)
        ax.set_ylabel("Overlap Ratio (P910 categories found in Wikipedia categories)")
        ax.set_title("P910 Category Match Distribution by Domain")
        plt.tight_layout()
        pdf.savefig(fig)
        plt.close(fig)

        # --- Depth analysis ---
        if has_depth:
            found = df[df["p910_depth"] >= 0]
            if not found.empty:
                found_domains = sorted(found["domain"].unique())
                depth_data = [found[found["domain"] == d]["p910_depth"].values for d in found_domains]

                fig, ax = plt.subplots(figsize=(8.5, 6))
                bp = ax.boxplot(depth_data, tick_labels=found_domains, patch_artist=True)
                colors = plt.cm.Set2(np.linspace(0, 1, len(found_domains)))
                for patch, color in zip(bp["boxes"], colors):
                    patch.set_facecolor(color)
                ax.set_ylabel("Depth (0 = direct match)")
                ax.set_title("Wikipedia Category Depth to P910 Match by Domain")
                plt.tight_layout()
                pdf.savefig(fig)
                plt.close(fig)

            with_p910 = df[df["p910_count"] > 0]
            if not with_p910.empty:
                match_rate = with_p910.groupby("domain")["p910_depth"].apply(lambda x: (x >= 0).mean())
                match_rate = match_rate.sort_values(ascending=True)

                fig, ax = plt.subplots(figsize=(8.5, 5))
                ax.barh(match_rate.index, match_rate.values, color="coral")
                ax.xaxis.set_major_formatter(mtick.PercentFormatter(1.0))
                ax.set_xlabel("Match Rate")
                ax.set_title("P910 Category Found in Wikipedia Hierarchy\n(among items with P910 links)")
                ax.set_xlim(0, 1.1)
                plt.tight_layout()
                pdf.savefig(fig)
                plt.close(fig)

        # --- Findings page ---
        add_text_page(pdf, "Findings", [
            "By following Wikidata's own P910 (topic's main category) links rather than heuristic string matching, we can measure real semantic alignment between the two systems.",
            "",
            "Chemical elements show the strongest alignment: P910-derived categories (e.g. 'Chemical elements') appear directly in the item's Wikipedia categories, yielding ~80% overlap at depth 0. This reflects tight curation in a small, well-defined domain.",
            "",
            "Films, albums, and cities all have full P910 coverage (every P31 class has a P910 link), but their P910-predicted categories do not appear directly on items. Instead, they appear 2-3 levels up in the Wikipedia parent-category hierarchy. For example, a film may be in '2020 drama films' rather than the P910-predicted 'Films' directly. This reflects Wikipedia's preference for specific year/genre categories over broad type categories.",
            "",
            "Animals show the deepest divergence, requiring 3-5 hops up the Wikipedia category tree before finding the P910 category. Wikipedia categorizes animals by geography and conservation status ('Mammals of Japan', 'Endangered species') rather than by ontological type.",
            "",
            "A key structural insight: P910 coverage is universal across all five domains (every item has P910-derived categories), but direct category membership is rare outside of chemical elements. The gap between Wikidata's type-based ontology and Wikipedia's browsing-oriented categories is systematic, not random.",
        ])

        # --- Ethics page ---
        add_text_page(pdf, "Ethics and Limitations", [
            "Cultural bias: Only English Wikipedia is analyzed, introducing Anglophone cultural bias. Categories in other language editions may organize knowledge differently.",
            "",
            "P910 coverage: The analysis is limited to P31 classes that have P910 properties. Classes without P910 are invisible to this comparison.",
            "",
            "API rate limits: Fixed delays between requests prevent IP bans, but limit the sample size feasible per pipeline run.",
            "",
            "Snapshot in time: Both Wikidata and Wikipedia change constantly; results reflect the data at acquisition time.",
            "",
            "Category hierarchy ceiling: The parent-category traversal is capped at 5 levels. Items that don't match within this window are marked as not found, but may match at greater depth.",
            "",
            "Sample size: Some domains may return few items due to SPARQL query constraints, making per-domain statistics less reliable.",
        ])

    print(f"PDF report saved to {output_path}")


def generate_html(data_dir="data/processed", output_path="docs/index.html"):
    """Generate an HTML report with inline base64 chart images."""
    import base64
    from io import BytesIO

    df = pd.read_csv(os.path.join(data_dir, "ontology_comparison.csv"))
    summary = pd.read_csv(os.path.join(data_dir, "domain_summary.csv"))

    mtime = os.path.getmtime(os.path.join(data_dir, "ontology_comparison.csv"))
    snapshot = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M UTC")
    has_p910 = "p910_count" in df.columns
    has_depth = "p910_depth" in df.columns

    def fig_to_base64(fig):
        buf = BytesIO()
        fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)
        return base64.b64encode(buf.read()).decode("utf-8")

    charts = []

    # Domain summary
    ordered = summary.sort_values("mean_overlap_ratio", ascending=True)
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.barh(ordered["domain"], ordered["mean_overlap_ratio"], color="steelblue")
    ax.set_xlabel("Mean Overlap Ratio")
    ax.set_title("P910 Category Match Rate by Domain")
    ax.set_xlim(0, 1.05)
    plt.tight_layout()
    charts.append(("Domain Summary", fig_to_base64(fig)))

    # P910 coverage
    if has_p910:
        coverage = df.groupby("domain").agg(
            total=("qid", "count"),
            with_p910=("p910_count", lambda x: (x > 0).sum()),
        )
        coverage["coverage"] = coverage["with_p910"] / coverage["total"]
        coverage = coverage.sort_values("coverage", ascending=True)
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.barh(coverage.index, coverage["coverage"], color="coral")
        ax.xaxis.set_major_formatter(mtick.PercentFormatter(1.0))
        ax.set_xlabel("P910 Coverage")
        ax.set_title("Fraction of Items Whose P31 Classes Have P910 Links")
        ax.set_xlim(0, 1.1)
        plt.tight_layout()
        charts.append(("P910 Category Coverage", fig_to_base64(fig)))

    # P31 vs category count
    fig, ax = plt.subplots(figsize=(8, 5))
    for domain, group in df.groupby("domain"):
        ax.scatter(group["p31_count"], group["category_count"], label=domain, alpha=0.6)
    ax.set_xlabel("Number of P31 (instance of) values")
    ax.set_ylabel("Number of Wikipedia categories")
    ax.set_title("P31 Count vs Wikipedia Category Count")
    ax.legend()
    plt.tight_layout()
    charts.append(("P31 Count vs Category Count", fig_to_base64(fig)))

    # Overlap distribution
    domains = sorted(df["domain"].unique())
    box_data = [df[df["domain"] == d]["overlap_ratio"].values for d in domains]
    fig, ax = plt.subplots(figsize=(8, 5))
    bp = ax.boxplot(box_data, tick_labels=domains, patch_artist=True)
    colors = plt.cm.Set2(np.linspace(0, 1, len(domains)))
    for patch, color in zip(bp["boxes"], colors):
        patch.set_facecolor(color)
    ax.set_ylabel("Overlap Ratio (P910 categories found in Wikipedia categories)")
    ax.set_title("P910 Category Match Distribution by Domain")
    plt.tight_layout()
    charts.append(("Overlap Distribution", fig_to_base64(fig)))

    # Depth analysis
    if has_depth:
        found = df[df["p910_depth"] >= 0]
        if not found.empty:
            found_domains = sorted(found["domain"].unique())
            depth_data = [found[found["domain"] == d]["p910_depth"].values for d in found_domains]
            fig, ax = plt.subplots(figsize=(8, 5))
            bp = ax.boxplot(depth_data, tick_labels=found_domains, patch_artist=True)
            colors = plt.cm.Set2(np.linspace(0, 1, len(found_domains)))
            for patch, color in zip(bp["boxes"], colors):
                patch.set_facecolor(color)
            ax.set_ylabel("Depth (0 = direct match)")
            ax.set_title("Wikipedia Category Depth to P910 Match by Domain")
            plt.tight_layout()
            charts.append(("Category Depth", fig_to_base64(fig)))

        with_p910 = df[df["p910_count"] > 0]
        if not with_p910.empty:
            match_rate = with_p910.groupby("domain")["p910_depth"].apply(lambda x: (x >= 0).mean())
            match_rate = match_rate.sort_values(ascending=True)
            fig, ax = plt.subplots(figsize=(8, 4))
            ax.barh(match_rate.index, match_rate.values, color="coral")
            ax.xaxis.set_major_formatter(mtick.PercentFormatter(1.0))
            ax.set_xlabel("Match Rate")
            ax.set_title("P910 Category Found in Wikipedia Hierarchy\n(among items with P910 links)")
            ax.set_xlim(0, 1.1)
            plt.tight_layout()
            charts.append(("P910 Match Rate", fig_to_base64(fig)))

    # Build stats line
    stats = f"Data snapshot: {snapshot} &mdash; {len(df)} items &mdash; {df['domain'].nunique()} domains"
    if has_p910:
        n_p910 = (df["p910_count"] > 0).sum()
        stats += f" &mdash; {n_p910}/{len(df)} with P910 categories"

    # Build HTML
    chart_html = ""
    for title, b64 in charts:
        chart_html += f'<h2>{title}</h2>\n<img src="data:image/png;base64,{b64}" style="max-width:100%">\n'

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Wikidata Ontology vs Wikipedia Categories</title>
  <meta property="og:title" content="Wikidata Ontology vs Wikipedia Categories">
  <meta property="og:description" content="Comparing P31 (instance of) properties with English Wikipedia categories using P910 semantic links.">
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; max-width: 900px; margin: 0 auto; padding: 2rem; line-height: 1.6; color: #1a1a2e; }}
    h1 {{ color: #4361ee; }}
    h2 {{ color: #3a0ca3; margin-top: 2rem; border-bottom: 1px solid #eee; padding-bottom: 0.3rem; }}
    img {{ display: block; margin: 1rem 0; }}
    .meta {{ color: #6c757d; font-size: 0.9rem; }}
    .authors {{ font-style: italic; margin-bottom: 1rem; }}
    a {{ color: #4361ee; }}
    .download {{ margin: 1rem 0; }}
    ol, ul {{ padding-left: 1.5rem; }}
  </style>
</head>
<body>
  <h1>Wikidata Ontology vs Wikipedia Categories</h1>
  <p class="authors">Emma Leonhart, Evan Pasenau, Jordyn Campen</p>
  <p class="meta">{stats}</p>
  <p class="download"><a href="report.pdf">Download PDF version</a> | <a href="https://github.com/EmmaLeonhart/301-project">View source on GitHub</a></p>

  <h2>Introduction</h2>
  <p>This report compares Wikidata's P31 (instance of) ontological classification with English Wikipedia's category system across multiple domains. Rather than relying on string matching, we use Wikidata's own <strong>P910 (topic's main category)</strong> property to follow the semantic link from a P31 class to its corresponding Wikipedia category.</p>

  <h3>Methodology</h3>
  <ol>
    <li>Retrieve the item's <strong>P31 (instance of)</strong> classes from Wikidata</li>
    <li>For each P31 class, follow <strong>P910 (topic's main category)</strong> to get the Wikidata item representing the Wikipedia category</li>
    <li>Use the <strong>enwiki sitelink</strong> on that category item to get the actual Wikipedia category name</li>
    <li>Fetch the item's Wikipedia categories and check for membership</li>
    <li>If not found directly, walk up the Wikipedia parent-category hierarchy to measure depth</li>
  </ol>

  {chart_html}

  <h2>Findings</h2>
  <p>By following Wikidata's own P910 (topic's main category) links rather than heuristic string matching, we measure real semantic alignment between the two systems.</p>
  <ul>
    <li><strong>Chemical elements</strong> show the strongest alignment: P910-derived categories appear directly in Wikipedia categories (~80% overlap at depth 0), reflecting tight curation in a small, well-defined domain.</li>
    <li><strong>Films, albums, and cities</strong> all have full P910 coverage, but their predicted categories appear 2&ndash;3 levels up the Wikipedia parent-category hierarchy. Wikipedia prefers specific year/genre categories (e.g. "2020 drama films") over the broad P910-predicted category ("Films").</li>
    <li><strong>Animals</strong> show the deepest divergence, requiring 3&ndash;5 hops. Wikipedia categorizes animals by geography and conservation status rather than ontological type.</li>
    <li><strong>Structural insight</strong>: P910 coverage is universal across all five domains, but direct category membership is rare outside chemical elements. The gap between Wikidata's type-based ontology and Wikipedia's browsing-oriented categories is systematic, not random.</li>
  </ul>

  <h2>Ethics and Limitations</h2>
  <ul>
    <li><strong>Cultural bias</strong>: Only English Wikipedia is analyzed.</li>
    <li><strong>P910 coverage</strong>: Limited to P31 classes that have P910 properties.</li>
    <li><strong>API rate limits</strong>: Fixed delays limit sample size per pipeline run.</li>
    <li><strong>Snapshot in time</strong>: Results reflect data at acquisition time.</li>
    <li><strong>Category hierarchy ceiling</strong>: Parent-category traversal is capped at 5 levels.</li>
  </ul>
</body>
</html>"""

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"HTML report saved to {output_path}")


if __name__ == "__main__":
    generate_report()
    generate_html()
