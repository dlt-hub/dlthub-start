# Sample Shop — your first dltHub workspace

The smallest complete trip through the full dltHub workflow: **ingest → load → deploy**. It loads a public sample online-shop REST API — and every step runs on dltHub Platform, so by the end you've taken a pipeline all the way to production.

## What's inside

| File | Purpose |
|------|---------|
| `pipeline.py` | dlt REST API pipeline — loads customers, orders, items, products, supplies, and stores |
| `__deployment__.py` | Declares which jobs are deployed to dltHub Platform |

## Run the pipeline on dltHub

```bash
cd <your-workspace>

# Deploy and run the pipeline (you'll be prompted to connect/login the first time)
uv run dlthub run load_sample_shop
```

## Watch the run

```bash
uv run dlthub job runs show pipeline.load_sample_shop
```

Open [app.dlthub.com](https://app.dlthub.com) to monitor and schedule your jobs.

## Make it yours

Edit `pipeline.py` to swap in your own source, then re-run with `uv run dlthub run load_sample_shop`.
