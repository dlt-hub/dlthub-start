# Sample Shop — your first dltHub workspace

A runnable dlt REST API pipeline (`pipeline.py`) that loads a sample online-shop
API to dltHub platform, plus an interactive onboarding notebook
(`notebooks/onboarding_success/`) that reads the loaded data back — your coding
agent deploys and runs these during onboarding.

To make it your own, edit `pipeline.py` or ask your coding agent to build a
pipeline for your own source.

## Onboarding notebook

`notebooks/onboarding_success/` is a marimo app, deployed alongside the pipeline
via `__deployment__.py`. It reads the loaded `sample_shop` data back from
`playground` so you can browse the schema and run your first query.

## Destination

The pipeline loads into `playground`, a **managed destination** provided by the
dltHub platform — no credentials or config needed. The platform resolves the name
and owns the (delta-based) storage, so data persists across runs. That's why
`playground` appears nowhere in `.dlt/config.toml` or the `dlt` libraries: it is
resolved in the backend.

You *can* repoint it — to a built-in destination like `duckdb` or one you've
configured yourself in `.dlt/config.toml`/secrets — but an arbitrary, unconfigured
name fails the run. For this onboarding pipeline, keep `playground`: it's the
zero-setup destination that lets the example run and persist without any extra
configuration.
