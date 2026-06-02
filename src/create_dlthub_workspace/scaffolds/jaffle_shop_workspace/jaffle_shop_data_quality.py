"""Data quality metrics and checks for the Jaffle Shop dataset."""

import dlt
import dlthub.data_quality as dq
from dlt.hub import run

from pipeline import jaffle_shop, load_data


@run.job(
    trigger=load_data.success,
    expose={"display_name": "Jaffle checks"},
)
def run_dq():
    source = jaffle_shop().add_limit(1)

    dq.with_metrics(
        source.orders,
        dq.metrics.table.row_count(),
        dq.metrics.column.null_count("subtotal"),
        dq.metrics.column.mean("order_total"),
    )

    pipeline = dlt.pipeline(
        pipeline_name="jaffle_shop_dq",
        destination="warehouse",
        dataset_name="jaffle_shop",
    )
    pipeline.run(source)

    dq.run_metrics(pipeline)
    dataset = pipeline.dataset()
    print(dq.read_metric(dataset, table="orders", metric="row_count").df())
    print(dq.read_metric(dataset, table="orders", column="subtotal", metric="null_count").df())
    print(dq.read_metric(dataset, table="orders", column="order_total", metric="mean").df())

    dq.run_checks(
        pipeline,
        checks={
            "orders": [
                dq.checks.is_not_null("id"),
                dq.checks.is_not_null("customer_id"),
                dq.checks.is_not_null("ordered_at"),
                dq.checks.is_not_null("order_total"),
            ],
            "products": [
                dq.checks.is_not_null("sku"),
                dq.checks.is_not_null("price"),
                dq.checks.is_in("type", ["beverage", "jaffle"]),
            ],
        },
    ).raise_on_failed_jobs()


if __name__ == "__main__":
    run_dq()
