# GitHub Actions: How the Pipeline Runs

## What Is GitHub Actions?

GitHub Actions is a CI/CD (Continuous Integration / Continuous Deployment) service
built into GitHub. It runs code in response to events — pushes, pull requests, cron
schedules, or manual triggers. The code runs on GitHub's servers, not on your local
machine.

## How It Works

When a workflow is triggered, GitHub:

1. **Spins up a virtual machine** — a fresh Ubuntu Linux VM (by default) with
   nothing on it except a base OS and common tools (git, curl, etc.)
2. **Checks out your repository** — clones your code into the VM
3. **Runs your steps** — installs dependencies, executes scripts, whatever you
   define
4. **Tears it down** — the VM is destroyed after the job finishes. Nothing persists
   between runs unless you explicitly commit it back to the repo or upload it as
   an artifact.

Each run starts from a completely clean state. There is no leftover state from
previous runs — no cached data, no installed packages, no environment variables
unless you set them up again.

## The Runner Environment

Our workflows use `runs-on: ubuntu-latest`, which gives us:

| Property | Value |
|----------|-------|
| **OS** | Ubuntu Linux (latest LTS, currently 22.04 or 24.04) |
| **CPU** | 2 cores |
| **RAM** | 7 GB |
| **Disk** | 14 GB |
| **Time limit** | 6 hours per job (default) |
| **Cost** | Free for public repositories |

GitHub also offers Windows (`windows-latest`) and macOS (`macos-latest`) runners,
but Linux is the standard choice — it's faster to boot, has better tooling support,
and is what most CI pipelines use.

**Important:** Because the runner is Linux, not Windows, any path handling or
shell commands in the workflow use Unix conventions (forward slashes, bash syntax).
This is true even if you develop on Windows locally.

## Our Workflows

We have three workflow files in `.github/workflows/`:

### `ci.yml` — Tests on Every Push

```yaml
on:
  push:
  pull_request:
```

Runs `pytest` on every push and pull request. If tests fail, the commit gets a red
X on GitHub. This is the safety net — it catches broken code before it lands.

**What it does:**
1. Checks out the repo
2. Installs Python 3.13
3. Installs dependencies from `requirements.txt`
4. Runs `python -m pytest tests/ -v`

### `pipeline.yml` — Weekly Data Pipeline

```yaml
on:
  schedule:
    - cron: "0 6 * * 1"  # Every Monday at 6 AM UTC
  workflow_dispatch:       # Manual trigger
```

This is the core automation. It runs the full data pipeline and commits the results
back to the repository.

**What it does:**
1. Checks out the repo
2. Installs Python + dependencies
3. Runs `python acquire.py 50` (fetches data from Wikidata + Wikipedia APIs)
   - Uses `continue-on-error: true` — if the Wikidata SPARQL endpoint is down,
     the pipeline continues with existing data
4. **Commits data immediately** — preserves fresh CSVs even if later steps fail
5. Installs Quarto + R + ggplot2 + TinyTeX (LaTeX distribution for PDF output)
6. Renders the Quarto report to PDF
7. Copies the PDF to `docs/` for download from the project site
8. Commits the report and pushes both commits

**Key detail:** Data and report are committed in separate steps. This two-commit
approach ensures that data is never lost to a rendering failure. Since all files
are tracked in git, every previous version is preserved in the commit history.

**Why `workflow_dispatch`?** This adds a "Run workflow" button in the GitHub Actions
tab, so you can trigger a run manually without waiting for the Monday schedule.

### `pages.yml` — Deploy GitHub Pages

```yaml
on:
  push:
    branches: [master]
    paths: [docs/**]
```

When anything in `docs/` changes (including the PDF copied there by the pipeline),
this workflow deploys the updated files to GitHub Pages.

## How the Pieces Fit Together

```
Monday 6 AM UTC (or manual trigger)
        │
        ▼
┌─ pipeline.yml ──────────────────────────┐
│  1. Fetch data from Wikidata + Wikipedia │
│     (continue-on-error if API is down)  │
│  2. Run analysis, save CSVs             │
│  3. Commit data (preserved immediately) │
│  4. Install TinyTeX, render Quarto → PDF│
│  5. Commit report + push                │
└────────────────┬────────────────────────┘
                 │ (push to master, docs/ changed)
                 ▼
┌─ pages.yml ────────────────────┐
│  Deploy docs/ to GitHub Pages  │
│  (includes downloadable PDF)   │
└────────────────────────────────┘

Every push (including pipeline commits)
        │
        ▼
┌─ ci.yml ───────────────┐
│  Run pytest             │
│  (catch broken code)    │
└─────────────────────────┘
```

## Why This Approach?

### No Server Required

The entire project — data acquisition, analysis, report generation, and publishing —
runs on ephemeral GitHub Actions VMs. There is no server to maintain, no database
daemon to keep running, no infrastructure to pay for.

### Reproducibility

Every pipeline run starts from scratch: clean OS, fresh dependency install, live API
queries. The results are committed to git with a date-stamped message. Anyone can
look at the commit history to see exactly what data was produced on what date, and
the code that produced it is in the same commit.

### Embeddable Databases Only

Because the runner is ephemeral (destroyed after each job), you cannot rely on a
persistent database server. Any database used in the pipeline must be **embeddable**
— it runs inside the Python process and stores data in a local file, like SQLite
for relational data or SutraDB for graph/RDF data. These get installed via `pip`
and require zero configuration.

This is a real constraint. You cannot use PostgreSQL, MySQL, Neo4j, or any other
database that requires a running server process (unless you set one up as a service
container in the workflow, which adds significant complexity). Embeddable databases
are the path of least resistance.

### Cost

GitHub Actions is free for public repositories with generous limits (2,000 minutes
per month for private repos on the free tier). Our pipeline run takes a few minutes,
so even running daily would use a trivial amount of the budget.

## Cron Schedule Syntax

The `schedule` trigger uses standard cron syntax:

```
┌───────────── minute (0-59)
│ ┌───────────── hour (0-23)
│ │ ┌───────────── day of month (1-31)
│ │ │ ┌───────────── month (1-12)
│ │ │ │ ┌───────────── day of week (0-6, Sunday=0)
│ │ │ │ │
0 6 * * 1    ← "At 06:00 UTC on Monday"
```

Note: GitHub Actions cron schedules can be delayed by up to 15 minutes during high
load. They also only run on the default branch (master).
