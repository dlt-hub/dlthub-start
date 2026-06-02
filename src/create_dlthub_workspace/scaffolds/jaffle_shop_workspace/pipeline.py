"""Jaffle Shop dlt pipeline.

Loads customers, orders, items, products, supplies, and stores
from the public Jaffle Shop REST API into a local warehouse.
"""

import dlt
from dlt.sources.rest_api import rest_api_source
from dlt.hub import run
from dlt.hub.run import trigger


pipeline = dlt.pipeline(
    pipeline_name="jaffle_shop",
    destination="warehouse",
    dataset_name="jaffle_shop",
)


def jaffle_shop():
    return rest_api_source(
        {
            "client": {
                "base_url": "https://jaffle-shop.dlthub.com/api/v1/",
                "paginator": {
                    "type": "header_link",
                },
            },
            "resources": [
                {"name": "customers", "primary_key": "id"},
                {"name": "orders", "primary_key": "id"},
                {"name": "items", "primary_key": "id"},
                {"name": "products", "primary_key": "sku"},
                {"name": "supplies", "primary_key": "id"},
                {"name": "stores", "primary_key": "id"},
            ],
        }
    )


@run.pipeline(
    pipeline,
    trigger=trigger.schedule("0 * * * *"),
    expose={"display_name": "Jaffle Shop pipeline"}
)
def load_data():
    """Load Jaffle Shop data from the public REST API."""
    load_info = pipeline.run(jaffle_shop().add_limit(1))
    print(load_info)


if __name__ == "__main__":
    load_data()
