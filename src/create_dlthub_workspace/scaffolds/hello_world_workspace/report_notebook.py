import marimo

__generated_with = "0.23.8"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import altair as alt
    import dlt

    return alt, dlt, mo


@app.cell(hide_code=True)
def _(dlt):
    """
    This cell is added for demonstration purposes: when running on dltHub Platform, the pipeline
    destination is a local DuckDB file that lives on the worker. To make that data accessible
    inside this notebook, we re-run the pipeline here so the local DuckDB is populated before
    any queries are made.

    Normally, if you use a cloud destination (e.g. MotherDuck or BigQuery), you would simply
    attach to the existing pipeline without re-running it:

        pipeline = dlt.attach("pipeline_name", destination="warehouse", dataset_name="dataset_name")
    """
    from pipeline import jaffle_shop
    pipeline_report = dlt.pipeline(
        pipeline_name="jaffle_shop_report",
        destination="warehouse",
        dataset_name="jaffle_shop",
    )
    load_info = pipeline_report.run(jaffle_shop().add_limit(1))
    return


@app.cell
def _(dlt):
    pipeline = dlt.attach("jaffle_shop_report")
    dataset = pipeline.dataset()
    return (dataset,)


@app.cell
def _(mo):
    mo.md("""
    # Jaffle Shop — Sales Overview
    """)
    return


@app.cell
def _(mo):
    mo.md("""
    ## When do orders peak?
    """)
    return


@app.cell
def _(dataset):
    df_chart1 = dataset("""
        SELECT
            CAST(EXTRACT(HOUR FROM ordered_at) AS INTEGER) AS hour_of_day,
            COUNT(*) AS orders
        FROM orders
        GROUP BY 1
        ORDER BY 1
    """).df()
    return (df_chart1,)


@app.cell
def _(alt, df_chart1, mo):
    _chart = alt.Chart(df_chart1).mark_bar(color="#4c78a8").encode(
        x=alt.X("hour_of_day:O", title="Hour of Day", axis=alt.Axis(labelAngle=0)),
        y=alt.Y("orders:Q", title="Number of Orders"),
        tooltip=["hour_of_day:O", "orders:Q"]
    ).properties(title="Orders by Hour of Day", width=500)
    mo.ui.altair_chart(_chart)
    return


@app.cell
def _(mo):
    mo.md("""
    ## Which products sell the most?
    """)
    return


@app.cell
def _(dataset):
    df_chart2 = dataset("""
        SELECT
            p.name AS product_name,
            p.type AS product_type,
            COUNT(i.id) AS units_sold
        FROM items i
        JOIN products p ON i.sku = p.sku
        GROUP BY p.name, p.type
        ORDER BY units_sold DESC
    """).df()
    return (df_chart2,)


@app.cell
def _(alt, df_chart2, mo):
    _chart = alt.Chart(df_chart2).mark_bar().encode(
        x=alt.X("units_sold:Q", title="Units Sold"),
        y=alt.Y("product_name:N", sort="-x", title="Product"),
        color=alt.Color("product_type:N", title="Type", scale=alt.Scale(scheme="category10")),
        tooltip=["product_name:N", "product_type:N", "units_sold:Q"]
    ).properties(title="Top Products by Units Sold", width=500)
    mo.ui.altair_chart(_chart)
    return


@app.cell
def _(mo):
    mo.md("""
    ## Revenue split: beverages vs jaffles
    """)
    return


@app.cell
def _(dataset):
    df_chart3 = dataset("""
        SELECT
            p.type AS product_type,
            COUNT(i.id) AS units_sold,
            ROUND(SUM(p.price), 2) AS total_revenue
        FROM items i
        JOIN products p ON i.sku = p.sku
        GROUP BY p.type
        ORDER BY total_revenue DESC
    """).df()
    return (df_chart3,)


@app.cell
def _(alt, df_chart3, mo):
    _chart = alt.Chart(df_chart3).mark_bar().encode(
        x=alt.X("product_type:N", title="Product Type", axis=alt.Axis(labelAngle=0)),
        y=alt.Y("total_revenue:Q", title="Total Revenue ($)"),
        color=alt.Color("product_type:N", legend=None, scale=alt.Scale(scheme="category10")),
        tooltip=["product_type:N", "units_sold:Q", "total_revenue:Q"]
    ).properties(title="Revenue by Product Type", width=300)
    mo.ui.altair_chart(_chart)
    return


if __name__ == "__main__":
    app.run()
