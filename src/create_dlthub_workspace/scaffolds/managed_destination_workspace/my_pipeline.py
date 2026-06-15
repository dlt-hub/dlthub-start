# Python internals
import os

# Other libraries
import dlt


@dlt.resource(table_name="items")
def items():
    yield {"id": 1, "name": "item_1"}
    yield {"id": 2, "name": "item_2"}


if __name__ == "__main__":
    pipeline = dlt.pipeline(
        pipeline_name="playground_example",
        destination="playground",
    )
    load_info = pipeline.run(items)
    print(load_info)
    print("Playground pipeline completed")
    print(f"RUNTIME__RUN_ID: {os.getenv('RUNTIME__RUN_ID')}")
