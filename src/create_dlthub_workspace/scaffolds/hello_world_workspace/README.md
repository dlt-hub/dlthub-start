# Hello World Workspace

Every programming language has a "Hello, World!" — the smallest possible program that proves the language works and shows you its essential shape. This workspace is the dltHub equivalent.

Just as `print("Hello, World!")` is not a useful program but a complete one, this workspace is not a production pipeline — it is a complete, working example of the full dltHub workflow: **ingest → load → visualise → deploy**. Once you have run it, you have touched every part of the platform.

---

A minimal dltHub workspace that loads the public [Jaffle Shop](https://jaffle-shop.dlthub.com) REST API into a local warehouse and visualises the data in a Marimo notebook.

## What's inside

| File | Purpose |
|------|---------|
| `pipeline.py` | dlt REST API pipeline — loads customers, orders, items, products, supplies, and stores |
| `report_notebook.py` | Marimo notebook — connects to the loaded data and renders charts |
| `__deployment__.py` | Declares which jobs are deployed to dltHub Platform |

## Run locally

```bash
cd workspace-name

# Load data
uv run python pipeline.py

# Open the notebook
uv run marimo edit report_notebook.py
```

## Deploy to dltHub Platform

```bash
uv run dlthub run
```

Then open [app.dlthub.com](https://app.dlthub.com) to monitor and schedule your jobs.

