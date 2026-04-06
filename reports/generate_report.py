"""Generate the project report as PDF + HTML from the analysis CSVs.

Uses only matplotlib (for the PDF charts) and builds a self-contained HTML page
with CSS bar charts — no Quarto, no Jupyter, no external rendering tools.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import numpy as np
from datetime import datetime
import textwrap


# ────────────────────────────────────────────────────────────────
#  Helpers
# ────────────────────────────────────────────────────────────────

def _load_data(data_dir="data/processed"):
    df = pd.read_csv(os.path.join(data_dir, "ontology_comparison.csv"))
    summary = pd.read_csv(os.path.join(data_dir, "domain_summary.csv"))
    mtime = os.path.getmtime(os.path.join(data_dir, "ontology_comparison.csv"))
    snapshot = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M UTC")
    return df, summary, snapshot


def _domain_depth_stats(df):
    """Return per-domain stats: items, mean_depth, match_rate, mean_p31, mean_cats."""
    rows = []
    for domain, group in df.groupby("domain"):
        with_p910 = group[group["p910_count"] > 0]
        found = group[group["p910_depth"] >= 0]
        rows.append({
            "domain": domain,
            "items": len(group),
            "with_p910": len(with_p910),
            "matched": len(found),
            "mean_depth": found["p910_depth"].mean() if len(found) > 0 else float("nan"),
            "median_depth": found["p910_depth"].median() if len(found) > 0 else float("nan"),
            "match_rate": len(found) / len(with_p910) if len(with_p910) > 0 else 0.0,
            "mean_p31": group["p31_count"].mean(),
            "mean_cats": group["category_count"].mean(),
            "mean_overlap": group["overlap_ratio"].mean(),
        })
    return pd.DataFrame(rows).sort_values("mean_depth", ascending=True, na_position="last")


# ────────────────────────────────────────────────────────────────
#  PDF generation
# ────────────────────────────────────────────────────────────────

def _wrap(text, width=95):
    return "\n".join(textwrap.wrap(text, width))


def _text_page(pdf, title, lines, fontsize=10):
    fig = plt.figure(figsize=(8.5, 11))
    fig.text(0.05, 0.95, title, fontsize=14, fontweight="bold", va="top")
    y = 0.90
    for line in lines:
        w = _wrap(line)
        fig.text(0.05, y, w, fontsize=fontsize, va="top", family="serif")
        y -= 0.04 * (w.count("\n") + 1)
        if y < 0.05:
            break
    plt.axis("off")
    pdf.savefig(fig)
    plt.close(fig)


def _table_page(pdf, title, col_labels, row_data, col_widths=None):
    """Render a data table as a PDF page."""
    fig, ax = plt.subplots(figsize=(8.5, 5))
    ax.axis("off")
    ax.set_title(title, fontsize=14, fontweight="bold", pad=20)
    table = ax.table(
        cellText=row_data,
        colLabels=col_labels,
        loc="center",
        cellLoc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1.0, 1.6)
    for key, cell in table.get_celld().items():
        if key[0] == 0:
            cell.set_facecolor("#4361ee")
            cell.set_text_props(color="white", fontweight="bold")
        else:
            cell.set_facecolor("#f8f9fa" if key[0] % 2 == 0 else "white")
    plt.tight_layout()
    pdf.savefig(fig)
    plt.close(fig)


def generate_report(data_dir="data/processed", output_path="reports/report.pdf"):
    df, summary, snapshot = _load_data(data_dir)
    stats = _domain_depth_stats(df)

    with PdfPages(output_path) as pdf:
        # Title
        fig = plt.figure(figsize=(8.5, 11))
        fig.text(0.5, 0.65, "Wikidata Ontology vs\nWikipedia Categories",
                 fontsize=22, fontweight="bold", ha="center", va="center")
        fig.text(0.5, 0.52, "Emma Leonhart, Evan Pasenau, Jordyn Campen",
                 fontsize=12, ha="center", va="center", style="italic")
        fig.text(0.5, 0.45, f"Data snapshot: {snapshot}  |  {len(df)} items  |  {df['domain'].nunique()} domains",
                 fontsize=10, ha="center", va="center", color="gray")
        plt.axis("off")
        pdf.savefig(fig)
        plt.close(fig)

        # Methodology
        _text_page(pdf, "Methodology", [
            "This report compares Wikidata's P31 (instance of) ontological classification with English Wikipedia's category system across five domains.",
            "",
            "For each item we follow Wikidata's own semantic links:",
            "  1. Retrieve the item's P31 (instance of) classes",
            "  2. For each P31 class, follow P910 (topic's main category) to get the Wikidata item for the Wikipedia category",
            "  3. Use the enwiki sitelink on that category item to get the actual Wikipedia category name",
            "  4. Fetch the item's Wikipedia categories and check for membership",
            "  5. If not a direct member, walk up the parent-category hierarchy and report the depth at which the P910 category is found",
            "",
            "This gives a principled measure of alignment: depth 0 means the item is directly in the predicted category, higher depths mean Wikipedia organizes the item under more specific subcategories.",
        ])

        # Summary table
        col_labels = ["Domain", "Items", "Mean Depth", "Match Rate", "Mean P31", "Mean Categories"]
        row_data = []
        for _, r in stats.iterrows():
            row_data.append([
                r["domain"].title(),
                str(r["items"]),
                f"{r['mean_depth']:.1f}" if not pd.isna(r["mean_depth"]) else "N/A",
                f"{r['match_rate']:.0%}",
                f"{r['mean_p31']:.1f}",
                f"{r['mean_cats']:.1f}",
            ])
        _table_page(pdf, "Domain Summary", col_labels, row_data)

        # Mean depth bar chart
        plot_stats = stats.dropna(subset=["mean_depth"]).sort_values("mean_depth", ascending=True)
        fig, ax = plt.subplots(figsize=(8.5, 5))
        bars = ax.barh(plot_stats["domain"], plot_stats["mean_depth"], color="steelblue")
        for bar, val in zip(bars, plot_stats["mean_depth"]):
            ax.text(bar.get_width() + 0.1, bar.get_y() + bar.get_height() / 2,
                    f"{val:.1f}", va="center", fontsize=10)
        ax.set_xlabel("Mean Depth (0 = direct category match)")
        ax.set_title("Mean Steps to P910 Category by Domain")
        plt.tight_layout()
        pdf.savefig(fig)
        plt.close(fig)

        # Findings
        _text_page(pdf, "Findings", [
            "Chemical elements show the strongest alignment: the P910-predicted Wikipedia category appears directly on every item (mean depth 0.0). This domain is small, well-defined, and tightly curated on both Wikidata and Wikipedia.",
            "",
            "Albums and cities require 2-3 steps up the Wikipedia category tree. Wikipedia places albums in year/genre subcategories ('2024 pop albums') rather than the broad P910-predicted category ('Albums'). Cities are filed under geographic subcategories ('Cities in Bavaria') rather than the generic 'Cities'.",
            "",
            "Films require about 3 steps. Like albums, Wikipedia uses fine-grained year/genre categories rather than a single 'Films' category.",
            "",
            "Animals show the deepest divergence at ~5 steps. Wikipedia organizes animals by geography and conservation status ('Mammals of Japan') rather than by biological classification, which is Wikidata's approach.",
            "",
            "The pattern is clear: domains where Wikipedia uses broad, type-based categories (chemical elements) align directly with Wikidata's P910 predictions. Domains where Wikipedia prefers specific browsing categories (films by year, animals by country) diverge at the surface but converge a few levels up the hierarchy.",
        ])

        # Ethics
        _text_page(pdf, "Ethics and Limitations", [
            "Cultural bias: Only English Wikipedia is analyzed. Other language editions may organize knowledge differently.",
            "",
            "P910 coverage: The analysis relies on P31 classes having P910 (topic's main category) properties. Classes without P910 are invisible to this comparison.",
            "",
            "API rate limits: Fixed delays between requests limit the sample size feasible per pipeline run.",
            "",
            "Snapshot in time: Both Wikidata and Wikipedia change constantly; results reflect the data at acquisition time.",
            "",
            "Category hierarchy ceiling: The parent-category traversal is capped at 5 levels. Items that do not match within this window may match at greater depth.",
            "",
            "Sample size: The animals domain returns few items due to SPARQL query constraints, making its statistics less reliable.",
        ])

    print(f"PDF report saved to {output_path}")


# ────────────────────────────────────────────────────────────────
#  HTML generation  (restores the full site structure)
# ────────────────────────────────────────────────────────────────

def generate_html(data_dir="data/processed", output_path="docs/index.html"):
    df, summary, snapshot = _load_data(data_dir)
    stats = _domain_depth_stats(df)
    total_items = len(df)
    n_domains = df["domain"].nunique()
    overall_mean_depth = df.loc[df["p910_depth"] >= 0, "p910_depth"].mean()

    # Build domain table rows
    domain_table_rows = ""
    for _, r in stats.iterrows():
        domain_table_rows += f"""        <tr>
          <td>{r['domain'].title()}</td><td>{r['items']}</td>
          <td>{r['mean_depth']:.1f}</td><td>{r['match_rate']:.0%}</td>
          <td>{r['mean_p31']:.1f}</td><td>{r['mean_cats']:.1f}</td>
        </tr>\n"""

    # Build CSS bar chart rows for mean depth
    bar_rows = ""
    plot_stats = stats.dropna(subset=["mean_depth"]).sort_values("mean_depth", ascending=False)
    max_depth = plot_stats["mean_depth"].max() if len(plot_stats) > 0 else 1
    for _, r in plot_stats.iterrows():
        pct = (r["mean_depth"] / max(max_depth, 0.1)) * 100
        pct = max(pct, 4)  # minimum bar width for label visibility
        bar_rows += f"""      <div class="bar-row">
        <div class="bar-label">{r['domain'].title()}</div>
        <div class="bar-track"><div class="bar-fill" style="width:{pct:.0f}%">{r['mean_depth']:.1f}</div></div>
      </div>\n"""

    # Domains sampled table
    from src.wikidata import DOMAINS
    domains_sampled_rows = ""
    for domain_name, classes in DOMAINS.items():
        for qid, label in classes.items():
            n = len(df[df["domain"] == domain_name])
            domains_sampled_rows += f"        <tr><td>{domain_name.replace('_', ' ').title()}</td><td>{label}</td><td>{qid}</td><td>{n}</td></tr>\n"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Wikidata Ontology vs Wikipedia Categories</title>
  <meta property="og:title" content="Wikidata Ontology vs Wikipedia Categories">
  <meta property="og:description" content="Comparing Wikidata P31 (instance of) with English Wikipedia categories using P910 semantic links across five domains.">
  <meta property="og:type" content="website">
  <meta name="theme-color" content="#4361ee">
  <style>
    :root {{
      --bg: #ffffff; --fg: #1a1a2e; --accent: #4361ee; --accent2: #3a0ca3;
      --muted: #6c757d; --card-bg: #f8f9fa; --border: #dee2e6; --code-bg: #e9ecef;
    }}
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; color: var(--fg); background: var(--bg); line-height: 1.7; }}
    .container {{ max-width: 960px; margin: 0 auto; padding: 0 1.5rem; }}
    header {{ background: linear-gradient(135deg, var(--accent2), var(--accent)); color: white; padding: 3rem 0; text-align: center; }}
    header h1 {{ font-size: 2.2rem; margin-bottom: 0.5rem; }}
    header p {{ font-size: 1.1rem; opacity: 0.9; }}
    .authors {{ margin-top: 1rem; font-size: 0.95rem; opacity: 0.8; }}
    nav {{ background: var(--card-bg); border-bottom: 1px solid var(--border); position: sticky; top: 0; z-index: 10; }}
    nav ul {{ list-style: none; display: flex; gap: 0; max-width: 960px; margin: 0 auto; padding: 0 1.5rem; }}
    nav a {{ display: block; padding: 0.75rem 1.25rem; color: var(--fg); text-decoration: none; font-size: 0.9rem; font-weight: 500; border-bottom: 2px solid transparent; transition: border-color 0.2s; }}
    nav a:hover {{ border-bottom-color: var(--accent); color: var(--accent); }}
    section {{ padding: 3rem 0; border-bottom: 1px solid var(--border); }}
    section:last-of-type {{ border-bottom: none; }}
    h2 {{ font-size: 1.6rem; margin-bottom: 1rem; color: var(--accent2); }}
    h3 {{ font-size: 1.2rem; margin: 1.5rem 0 0.5rem; }}
    p, li {{ margin-bottom: 0.75rem; }}
    ul, ol {{ padding-left: 1.5rem; }}
    code {{ background: var(--code-bg); padding: 0.15em 0.4em; border-radius: 3px; font-size: 0.9em; }}
    pre {{ background: var(--fg); color: #e0e0e0; padding: 1rem 1.25rem; border-radius: 6px; overflow-x: auto; font-size: 0.85rem; margin: 1rem 0; }}
    pre code {{ background: none; padding: 0; color: inherit; }}
    .card-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 1.25rem; margin: 1.5rem 0; }}
    .card {{ background: var(--card-bg); border: 1px solid var(--border); border-radius: 8px; padding: 1.25rem; }}
    .card h4 {{ margin-bottom: 0.5rem; color: var(--accent); }}
    .card .stat {{ font-size: 2rem; font-weight: 700; color: var(--accent2); }}
    .card .label {{ font-size: 0.85rem; color: var(--muted); }}
    table {{ width: 100%; border-collapse: collapse; margin: 1rem 0; font-size: 0.9rem; }}
    th, td {{ padding: 0.6rem 0.75rem; text-align: left; border-bottom: 1px solid var(--border); }}
    th {{ background: var(--card-bg); font-weight: 600; }}
    tr:hover td {{ background: #f0f4ff; }}
    .bar-chart {{ margin: 1.5rem 0; }}
    .bar-row {{ display: flex; align-items: center; margin-bottom: 0.6rem; }}
    .bar-label {{ width: 150px; font-size: 0.9rem; font-weight: 500; text-align: right; padding-right: 1rem; flex-shrink: 0; }}
    .bar-track {{ flex: 1; background: var(--code-bg); border-radius: 4px; height: 28px; position: relative; }}
    .bar-fill {{ height: 100%; border-radius: 4px; background: linear-gradient(90deg, var(--accent), var(--accent2)); display: flex; align-items: center; padding-left: 0.5rem; color: white; font-size: 0.8rem; font-weight: 600; min-width: 2.5rem; }}
    .pipeline {{ display: flex; align-items: center; gap: 0; margin: 2rem 0; flex-wrap: wrap; justify-content: center; }}
    .pipeline-step {{ background: var(--card-bg); border: 2px solid var(--accent); border-radius: 8px; padding: 1rem 1.25rem; text-align: center; min-width: 150px; }}
    .pipeline-step strong {{ display: block; color: var(--accent2); }}
    .pipeline-step span {{ font-size: 0.8rem; color: var(--muted); }}
    .pipeline-arrow {{ font-size: 1.5rem; color: var(--accent); padding: 0 0.5rem; }}
    footer {{ text-align: center; padding: 2rem 0; color: var(--muted); font-size: 0.85rem; }}
    footer a {{ color: var(--accent); }}
    .download-btn {{ display: inline-block; margin-top: 1.25rem; padding: 0.7rem 1.5rem; background: white; color: var(--accent2); text-decoration: none; font-weight: 600; border-radius: 6px; font-size: 1rem; transition: background 0.2s, transform 0.1s; }}
    .download-btn:hover {{ background: #e8e8ff; transform: translateY(-1px); }}
    @media (max-width: 600px) {{
      header h1 {{ font-size: 1.5rem; }}
      nav ul {{ flex-wrap: wrap; }}
      .bar-label {{ width: 100px; font-size: 0.8rem; }}
      .pipeline {{ flex-direction: column; }}
      .pipeline-arrow {{ transform: rotate(90deg); }}
    }}
  </style>
</head>
<body>

<header>
  <div class="container">
    <h1>Wikidata Ontology vs Wikipedia Categories</h1>
    <p>Assessing categorization consistency across knowledge domains</p>
    <div class="authors">Emma Leonhart &middot; Evan Pasenau &middot; Jordyn Campen &mdash; COSC 301</div>
    <a href="report.pdf" download class="download-btn">Download Report (PDF)</a>
  </div>
</header>

<nav>
  <ul>
    <li><a href="#questions">Questions</a></li>
    <li><a href="#methodology">Methodology</a></li>
    <li><a href="#pipeline">Pipeline</a></li>
    <li><a href="#findings">Findings</a></li>
    <li><a href="#ethics">Ethics</a></li>
  </ul>
</nav>

<!-- QUESTIONS -->
<section id="questions">
  <div class="container">
    <h2>Analytics Questions</h2>
    <ol>
      <li><strong>Do Wikipedia categories line up with the Wikidata ontology?</strong> &mdash; We follow Wikidata's P910 (topic's main category) link from each P31 class to its corresponding Wikipedia category and check whether items are actually placed in that category.</li>
      <li><strong>Do they align more in certain domains?</strong> &mdash; We sample five domains (animals, films, cities, chemical elements, albums) and compare how many steps up the Wikipedia category tree are needed to find the P910-predicted category.</li>
      <li><strong>Are some categories of information easier to categorize than others?</strong> &mdash; We measure depth variance within each domain to identify which areas have consistent vs. inconsistent classification.</li>
    </ol>
  </div>
</section>

<!-- METHODOLOGY -->
<section id="methodology">
  <div class="container">
    <h2>Methodology</h2>

    <h3>Data Sources</h3>
    <div class="card-grid">
      <div class="card">
        <h4>Wikidata</h4>
        <p>SPARQL queries against the <a href="https://query.wikidata.org/">Wikidata Query Service</a> fetch items that are <code>P31</code> (instance&nbsp;of) a target class, their P31 values, and the <code>P910</code> (topic's main category) links on those classes.</p>
      </div>
      <div class="card">
        <h4>English Wikipedia</h4>
        <p>The <a href="https://en.wikipedia.org/w/api.php">Wikipedia API</a> retrieves non-hidden categories for each article, plus parent categories up to 5 levels deep.</p>
      </div>
    </div>

    <h3>Domains Sampled</h3>
    <table>
      <thead><tr><th>Domain</th><th>Wikidata Class</th><th>QID</th><th>Items</th></tr></thead>
      <tbody>
{domains_sampled_rows}      </tbody>
    </table>

    <h3>P910 Category Matching</h3>
    <p>For each item, we follow its P31 class's <code>P910</code> (topic's main category) property to find the Wikidata item for the corresponding Wikipedia category. We then use that item's English Wikipedia sitelink to get the actual category name (e.g. <code>Q7378</code> &rarr; <code>Category:Mammals</code>). If the P31 class lacks P910, we walk up the <code>P279</code> (subclass of) hierarchy until we find a class that has one.</p>
    <p>We then check whether the item is directly in that Wikipedia category. If not, we walk up the parent-category chain and report the <strong>depth</strong> at which the P910-predicted category first appears:</p>
    <pre><code>depth = 0  &rarr;  item is directly in the P910 category
depth = 1  &rarr;  P910 category is one level up (parent of a direct category)
depth = N  &rarr;  P910 category is N levels up the hierarchy</code></pre>
  </div>
</section>

<!-- PIPELINE -->
<section id="pipeline">
  <div class="container">
    <h2>Data Pipeline</h2>

    <div class="pipeline">
      <div class="pipeline-step"><strong>1. Acquire</strong><span>wikidata.py + wikipedia.py</span></div>
      <div class="pipeline-arrow">&rarr;</div>
      <div class="pipeline-step"><strong>2. Merge &amp; Clean</strong><span>etl.py</span></div>
      <div class="pipeline-arrow">&rarr;</div>
      <div class="pipeline-step"><strong>3. Analyze</strong><span>analysis.py</span></div>
      <div class="pipeline-arrow">&rarr;</div>
      <div class="pipeline-step"><strong>4. Report</strong><span>generate_report.py</span></div>
    </div>

    <h3>Step 1: Acquire</h3>
    <p><code>src/wikidata.py</code> sends SPARQL queries to fetch P31 items with English Wikipedia sitelinks, then resolves <code>P910</code> category links for each P31 class (walking up <code>P279</code> if needed). <code>src/wikipedia.py</code> fetches categories and parent-category chains via the Wikipedia API.</p>

    <h3>Step 2: Merge &amp; Clean</h3>
    <p><code>src/etl.py</code> joins Wikidata P31/P910 data with Wikipedia categories into a single DataFrame, computing depth to P910 match for each item.</p>

    <h3>Step 3: Analyze</h3>
    <p><code>src/analysis.py</code> computes per-item overlap ratios and domain-level summaries (mean depth, match rates).</p>

    <h3>Step 4: Report</h3>
    <p><code>reports/generate_report.py</code> reads the CSVs and generates this HTML page and a PDF report. No external rendering tools required.</p>

    <h3>Running It</h3>
    <pre><code>pip install -r requirements.txt
python acquire.py 50                  # fetch 50 items per domain
python reports/generate_report.py     # generate HTML + PDF
python -m pytest tests/ -v            # run tests</code></pre>
  </div>
</section>

<!-- FINDINGS -->
<section id="findings">
  <div class="container">
    <h2>Findings</h2>

    <div class="card-grid">
      <div class="card"><div class="stat">{total_items}</div><div class="label">Total items analyzed</div></div>
      <div class="card"><div class="stat">{n_domains}</div><div class="label">Domains compared</div></div>
      <div class="card"><div class="stat">{overall_mean_depth:.1f}</div><div class="label">Overall mean depth to P910 match</div></div>
    </div>

    <h3>Mean Steps to P910 Category by Domain</h3>
    <div class="bar-chart">
{bar_rows}    </div>

    <h3>Domain Summary</h3>
    <table>
      <thead>
        <tr><th>Domain</th><th>Items</th><th>Mean Depth</th><th>Match Rate</th><th>Mean P31 Count</th><th>Mean Categories</th></tr>
      </thead>
      <tbody>
{domain_table_rows}      </tbody>
    </table>

    <h3>Key Observations</h3>
    <ol>
      <li><strong>Chemical elements align directly.</strong> The P910-predicted category appears on every item at depth 0. This domain is small, well-defined, and tightly curated on both systems.</li>
      <li><strong>Albums and cities need 2&ndash;3 steps.</strong> Wikipedia files albums under year/genre subcategories ("2024 pop albums") and cities under geographic subcategories ("Cities in Bavaria") rather than the broad P910 category.</li>
      <li><strong>Films need about 3 steps.</strong> Same pattern as albums &mdash; Wikipedia uses fine-grained year/genre categories rather than a single "Films" category.</li>
      <li><strong>Animals diverge the most (~5 steps).</strong> Wikipedia organizes animals by geography and conservation status ("Mammals of Japan") rather than by biological classification, which is Wikidata's approach.</li>
      <li><strong>The pattern:</strong> domains where Wikipedia uses broad, type-based categories align directly with Wikidata. Domains where Wikipedia favors specific browsing categories (by year, by country) diverge at the surface but converge higher up the hierarchy.</li>
    </ol>

    <h3>Answering Our Questions</h3>
    <div class="card-grid">
      <div class="card">
        <h4>Q1: Do Wikipedia categories line up with Wikidata ontology?</h4>
        <p><strong>Sometimes directly, always eventually.</strong> Following P910 links, every domain converges &mdash; the question is how many steps up the Wikipedia category tree it takes. Chemical elements match at depth 0; animals need ~5 levels.</p>
      </div>
      <div class="card">
        <h4>Q2: Do they align more in certain domains?</h4>
        <p><strong>Yes.</strong> Small, well-defined domains (chemical elements) align at the surface. Domains with richer Wikipedia categorization schemes (films, animals) require climbing the hierarchy.</p>
      </div>
      <div class="card">
        <h4>Q3: Are some easier to categorize?</h4>
        <p><strong>Yes.</strong> Domains with simple type labels that Wikipedia uses directly are easiest. Domains where Wikipedia prefers geographic, temporal, or genre-based categories over type-based ones show deeper divergence.</p>
      </div>
    </div>
  </div>
</section>

<!-- ETHICS -->
<section id="ethics">
  <div class="container">
    <h2>Ethics &amp; Limitations</h2>
    <ul>
      <li><strong>Cultural bias:</strong> Only English Wikipedia is analyzed, reflecting the interests and knowledge of English-speaking editors.</li>
      <li><strong>P910 coverage:</strong> The analysis relies on P31 classes having P910 properties. Classes without P910 are invisible to this comparison.</li>
      <li><strong>Sample size:</strong> The animals domain returned only {len(df[df['domain'] == 'animals'])} items due to SPARQL query constraints. Results for this domain are not statistically robust.</li>
      <li><strong>API rate limits:</strong> All requests include rate limiting and a descriptive User-Agent header.</li>
      <li><strong>Snapshot in time:</strong> Both Wikidata and Wikipedia change constantly; results reflect the data at acquisition time ({snapshot}).</li>
      <li><strong>Category hierarchy ceiling:</strong> Parent-category traversal is capped at 5 levels. Items that do not match within this window may match at greater depth.</li>
    </ul>
  </div>
</section>

<footer>
  <div class="container">
    <p>COSC 301 &mdash; Data Analytics &middot; <a href="https://github.com/EmmaLeonhart/301-project">View source on GitHub</a></p>
  </div>
</footer>

</body>
</html>"""

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"HTML report saved to {output_path}")


if __name__ == "__main__":
    generate_report()
    generate_html()
