# Sample Shop — your first dltHub workspace

A runnable dlt REST API pipeline (`pipeline.py`) that loads a sample online-shop
API to dltHub Platform — already run for you during setup.

To make it your own, edit `pipeline.py` or ask your coding agent to build a
pipeline for your own source.

## Destination

The pipeline loads into `playground`, a **managed destination** provided by the
dltHub Platform — no credentials or config needed. The platform resolves the name
and owns the (delta-based) storage, so data persists across runs. That's why
`playground` appears nowhere in `.dlt/config.toml` or the `dlt` libraries: it is
resolved in the backend.

You *can* repoint it — to a built-in destination like `duckdb` or one you've
configured yourself in `.dlt/config.toml`/secrets — but an arbitrary, unconfigured
name fails the run. For this onboarding pipeline, keep `playground`: it's the
zero-setup destination that lets the example run and persist without any extra
configuration.
