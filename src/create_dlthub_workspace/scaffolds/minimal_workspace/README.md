# Sample Shop — your first dltHub workspace

The smallest complete trip through the full dltHub workflow: **ingest → load → visualise → deploy**. It loads a public sample online-shop REST API and charts it in a Marimo notebook — and every step runs on dltHub Platform, so by the end you've taken a pipeline all the way to production.

## What's inside

| File | Purpose |
|------|---------|
| `pipeline.py` | dlt REST API pipeline — loads customers, orders, items, products, supplies, and stores |
| `report_notebook.py` | Marimo notebook — connects to the loaded data and renders charts |
| `__deployment__.py` | Declares which jobs are deployed to dltHub Platform |

## Run the pipeline on dltHub

```bash
cd <your-workspace>

# Deploy and run the pipeline (you'll be prompted to connect/login the first time)
uv run dlthub run load_data
```

## Watch the run

```bash
uv run dlthub job runs show pipeline.load_data
```

Open [app.dlthub.com](https://app.dlthub.com) to monitor and schedule your jobs.

## Visualise the data

Deploy the notebook as a read-only web app on the Platform:

```bash
uv run dlthub job serve report_notebook
```

## Make it yours

Edit `pipeline.py` to swap in your own source, then re-run with `uv run dlthub run load_data`.
