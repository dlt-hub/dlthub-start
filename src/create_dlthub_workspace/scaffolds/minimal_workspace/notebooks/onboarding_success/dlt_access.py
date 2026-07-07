"""Read-only access to the sample_shop data in the playground destination.

Reads via the same pipeline handle pipeline.py loads with, so the runtime
resolves `playground` for us.
"""

from __future__ import annotations

from functools import lru_cache

import dlt
import pandas as pd

# Must match pipeline.py.
PIPELINE_NAME = "sample_shop_pipeline"
DATASET_NAME = "sample_shop"
DESTINATION_NAME = "playground"
RAW_PIPELINE = "sample_shop"
DESTINATION = "playground"

_HIDDEN_COLUMNS = {"_dlt_load_id", "_dlt_id", "_dlt_parent_id", "_dlt_list_idx"}
_HIDDEN_TABLES = {"orders__items"}

# PK/FK per table (dlt has no native FK concept; fk_targets maps col -> "table.col").
KEYS = {
    "customers": {"pk": {"id"}, "fk": set(), "fk_targets": {}},
    "orders":    {"pk": {"id"}, "fk": {"customer_id", "store_id"},
                  "fk_targets": {"customer_id": "customers.id", "store_id": "stores.id"}},
    "items":     {"pk": {"id"}, "fk": {"order_id", "sku"},
                  "fk_targets": {"order_id": "orders.id", "sku": "products.sku"}},
    "products":  {"pk": {"sku"}, "fk": set(), "fk_targets": {}},
    "supplies":  {"pk": {"id"}, "fk": {"sku"}, "fk_targets": {"sku": "products.sku"}},
    "stores":    {"pk": {"id"}, "fk": set(), "fk_targets": {}},
}


def key_role(table: str, column: str) -> str | None:
    keys = KEYS.get(table)
    if not keys:
        return None
    if column in keys["pk"]:
        return "pk"
    if column in keys["fk"]:
        return "fk"
    return None


@lru_cache(maxsize=1)
def _dataset():
    pipeline = dlt.pipeline(
        pipeline_name=PIPELINE_NAME,
        destination=DESTINATION_NAME,
        dataset_name=DATASET_NAME,
    )
    return pipeline.dataset()


@lru_cache(maxsize=1)
def _scan() -> tuple[dict, dict]:
    schema = _dataset().schema
    columns: dict[str, list[tuple[str, str]]] = {}
    producer: dict[str, str] = {}
    for table in schema.data_table_names():
        if table in _HIDDEN_TABLES:
            continue
        cols = schema.get_table_columns(table)
        columns[table] = [
            (col, c.get("data_type", "unknown"))
            for col, c in cols.items()
            if col not in _HIDDEN_COLUMNS
        ]
        producer[table] = RAW_PIPELINE
    return columns, producer


def list_tables() -> list[str]:
    return list(_scan()[0].keys())


def get_columns(table: str) -> list[tuple[str, str]]:
    return _scan()[0].get(table, [])


def get_columns_sorted(table: str) -> list[tuple[str, str]]:
    keys = KEYS.get(table, {})
    pk_set = keys.get("pk", set())
    fk_set = keys.get("fk", set())

    def _key(item):
        col, _ = item
        if col in pk_set:
            return (0, col)
        if col in fk_set:
            return (1, col)
        return (2, col)

    return sorted(get_columns(table), key=_key)


def pipeline_of(table: str) -> str | None:
    return _scan()[1].get(table)


def get_table_type(table: str) -> str:
    return "table"


def run_query(sql: str) -> pd.DataFrame:
    with _dataset().sql_client as client:
        with client.execute_query(sql) as cursor:
            return cursor.df()


def default_query(table: str) -> str:
    return f'SELECT *\nFROM "{table}"\nLIMIT 100'


def _row_count(table: str):
    try:
        return int(run_query(f'SELECT COUNT(*) AS n FROM "{table}"')["n"][0])
    except Exception:
        return None


def overview_payload(pipeline: str = RAW_PIPELINE) -> list[dict]:
    tables = [t for t in list_tables() if pipeline_of(t) == pipeline]
    if "orders" in tables:
        tables = ["orders"] + [t for t in tables if t != "orders"]
    payload = []
    for table in tables:
        fk_targets = KEYS.get(table, {}).get("fk_targets", {})
        payload.append({
            "table": table,
            "rows": _row_count(table),
            "columns": [
                {
                    "name": col,
                    "type": dtype,
                    "role": key_role(table, col) or "",
                    "fk_target": fk_targets.get(col, "") if key_role(table, col) == "fk" else "",
                }
                for col, dtype in get_columns_sorted(table)
            ],
        })
    return payload
