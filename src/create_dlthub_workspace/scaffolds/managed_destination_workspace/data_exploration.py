# Python internals
import os

# Other libraries
import dlt

if __name__ == "__main__":
    pipeline = dlt.pipeline(
        pipeline_name="playground_example",
        destination="playground",
    )
    tbl = pipeline.dataset().items.arrow()
    print(f"destination read-back: items={tbl.num_rows} rows")
    print(tbl.to_pydict())
    print("Playground data reader completed")
    print(f"RUNTIME__RUN_ID: {os.getenv('RUNTIME__RUN_ID')}")
