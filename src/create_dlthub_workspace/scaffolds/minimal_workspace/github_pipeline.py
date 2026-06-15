"""GitHub dlt pipeline.

Loads the 50 most recent issues from dlt-hub/dlt into DuckDB.
"""

import dlt
from dlt.sources.rest_api import rest_api_source
from dlt.hub import run


def github():
    return rest_api_source(
        {
            "client": {
                "base_url": "https://api.github.com/",
            },
            "resources": [
                {
                    "name": "issues",
                    "endpoint": {
                        "path": "repos/dlt-hub/dlt/issues",
                        "params": {
                            "state": "all",
                            "sort": "created",
                            "direction": "desc",
                        },
                    },
                    "primary_key": "id",
                },
            ],
        }
    )


@run.pipeline("github_pipeline")
def load_github():
    """Load the 50 most recent issues from dlt-hub/dlt."""

    pipeline = dlt.pipeline(
        pipeline_name="github_pipeline",
        destination="warehouse",
        dataset_name="github",
    )

    load_info = pipeline.run(github().add_limit(50, count_rows=True), write_disposition="replace")
    print(load_info)


if __name__ == "__main__":
    load_github()