import marimo

__generated_with = "0.23.10"
app = marimo.App(
    width="full",
    app_title="dltHub · First pipeline",
    css_file="styles/app.css",
    html_head_file="styles/head.html",
)


@app.cell
def _():
    import asyncio
    import html
    from pathlib import Path

    import numpy as np
    import pandas as pd

    import marimo as mo

    import dlt_access as da
    from widgets.action_button import ActionButton
    from widgets.schema_overview import SchemaOverview
    from widgets.scroll_cue import ScrollCue

    return ActionButton, Path, SchemaOverview, ScrollCue, asyncio, da, html, mo, np, pd


@app.cell
def _(Path, mo):
    _css = (Path(__file__).parent / "styles" / "onboarding_shell.css").read_text()
    shell_css = mo.Html(f"<style>{_css}</style>")

    CARD_STYLE = {
        "background": "var(--dlt-card)",
        "border": "var(--dlt-card-border)",
        "border-radius": "var(--dlt-radius)",
        "box-shadow": "var(--dlt-shadow)",
        "box-sizing": "border-box",
    }
    COLUMN_STYLE = {
        "max-width": "1120px",
        "margin": "0 auto",
        "padding": "44px 24px 72px",
        "box-sizing": "border-box",
    }

    def page_header(title, subtitle):
        return mo.Html(
            '<div class="page-head">'
            f'<h2 class="page-title">{title}</h2>'
            f'<p class="page-subtitle">{subtitle}</p>'
            "</div>"
        )

    shell_css
    return CARD_STYLE, COLUMN_STYLE, page_header


@app.cell
def _(ActionButton, mo):
    run_button = mo.ui.anywidget(
        ActionButton(label="Run Query", variant="start", icon="run", size="lg")
    )
    to_next = mo.ui.anywidget(
        ActionButton(label="Next step", variant="primary", size="lg", route="org-setup")
    )
    return run_button, to_next


@app.cell
def _(mo):
    get_data, set_data = mo.state(None)
    return get_data, set_data


@app.cell
def _(SchemaOverview, get_data, mo):
    _d = get_data()
    if _d is not None:
        schema_overview = mo.ui.anywidget(SchemaOverview(payload=_d["payload"]))
    else:
        schema_overview = None
    return (schema_overview,)


@app.cell
def _(da, get_data, mo, schema_overview):
    _d = get_data()
    if schema_overview is not None and _d is not None:
        _table = "orders" if "orders" in _d["tables"] else _d["tables"][0]
        sql_editor = mo.ui.code_editor(
            value=schema_overview.query_build or da.default_query(_table),
            language="sql", label="", min_height=120, max_height=160,
        )
    else:
        sql_editor = None
    return (sql_editor,)


@app.cell
def _(
    CARD_STYLE,
    COLUMN_STYLE,
    ScrollCue,
    da,
    html,
    mo,
    np,
    pd,
    page_header,
    run_button,
    schema_overview,
    sql_editor,
    to_next,
):
    def _spark(series):
        s = series.dropna()
        if not len(s):
            return ""
        counts = (
            list(np.histogram(s.astype(float), bins=10)[0])
            if pd.api.types.is_numeric_dtype(s)
            else series.astype(str).value_counts().head(10).tolist()
        )
        mx = max(counts) if counts else 0
        if not mx:
            return ""
        bars = "".join(
            f'<span class="spark-bar" style="height:{max(10, round(h / mx * 100))}%"></span>'
            for h in counts
        )
        return f'<div class="spark">{bars}</div>'

    def _results_html(sql):
        df = da.run_query(sql)
        df = df[[c for c in df.columns if not c.startswith("_dlt")]]
        cols = list(df.columns)
        head = "".join(
            f"<th><div class='th-name'>{html.escape(str(c))}</div>{_spark(df[c])}</th>"
            for c in cols
        )
        body = "".join(
            "<tr>" + "".join(f"<td>{html.escape(str(r[c]))}</td>" for c in cols) + "</tr>"
            for _, r in df.head(500).iterrows()
        )
        n = len(df)
        toggle = (
            '<label for="res-expand" class="res-toggle">'
            '<span class="lbl-more">Show all</span>'
            '<span class="lbl-less">Show less</span></label>'
        ) if n > 8 else ""
        return (
            '<input type="checkbox" id="res-expand" class="res-expand-cb">'
            '<div class="dlt-table-wrap res-collapsible"><table class="dlt-table">'
            f"<thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>"
            f'<div class="res-foot"><span class="dlt-muted">{n} rows</span>{toggle}</div>'
        )

    _study_head = page_header(
        f"Congrats! Your first pipeline successfully loaded data "
        f"from the sample shop API into {da.DESTINATION}.",
        "Take a quick look at your data, then run your first query.",
    )

    if schema_overview is None or sql_editor is None:
        _rows = "".join(
            f'<div class="sk-row"><span class="sk-dot"></span>'
            f'<span class="sk-line {w}"></span></div>'
            for w in ("sk-w55", "sk-w40", "sk-w70", "sk-w30", "sk-w55", "sk-w40")
        )
        _content = [
            _study_head,
            mo.Html(
                '<div class="dlt-skeleton">'
                f'<div class="sk-pane sk-schema">{_rows}</div>'
                '<div class="sk-pane sk-workspace">'
                '<div class="sk-block"></div><div class="sk-block tall"></div>'
                "</div></div>"
            ),
        ]
    else:
        queried = run_button.clicks > 0
        _schema_pane = mo.vstack([schema_overview], gap=0).style(
            {**CARD_STYLE, "flex": "1 1 300px", "min-width": "260px"}
        )
        if queried:
            try:
                _inner = _results_html(sql_editor.value)
            except Exception as err:
                _inner = (
                    '<div class="dlt-muted" style="color:var(--dlt-danger)">'
                    f"Query error: {html.escape(str(err))}</div>"
                )
            _results = mo.Html(
                '<div class="dlt-section-label">Results</div>'
                f'<div class="res-block">{_inner}</div>'
            )
        else:
            _results = mo.Html(
                '<div class="res-empty">Run the query to see your rows here.</div>'
            )
        _run_row = mo.hstack(
            [run_button] + (
                [] if queried
                else [mo.Html(
                    '<span class="run-hint"><span class="run-arrow">&larr;</span>'
                    "Run your first query</span>"
                )]
            ),
            justify="start", align="center", gap=0.6,
        )
        _workspace_pane = mo.vstack([sql_editor, _run_row, _results], gap=0.7).style(
            {**CARD_STYLE, "padding": "18px 20px", "flex": "3 1 480px", "min-width": "320px"}
        )
        _workbench = mo.hstack(
            [_schema_pane, _workspace_pane], gap=1, align="stretch", wrap=True
        )
        _content = [
            _study_head,
            _workbench,
        ]
        if queried:
            _content.append(
                mo.vstack(
                    [mo.hstack([to_next], justify="center"),
                     mo.Html('<div class="dlt-next-anchor"></div>')],
                    gap=0,
                ).style({"animation": "fade-in 0.3s ease"})
            )
            _content.append(mo.ui.anywidget(ScrollCue()))

    mo.vstack(_content, gap=1.25).style(COLUMN_STYLE)
    return

@app.cell
async def _(asyncio, da, get_data, mo, set_data):
    # Load only when served as an app (mode "run"). Skipping during export keeps
    # the snapshot at the header+skeleton state, so it caches cleanly (no
    # anywidget) and the live kernel loads the data on open.
    if mo.app_meta().mode == "run" and get_data() is None:
        def _load():
            return {
                "payload": da.overview_payload("sample_shop"),
                "tables": [t for t in da.list_tables() if da.pipeline_of(t) == "sample_shop"],
            }
        set_data(await asyncio.to_thread(_load))
    return

if __name__ == "__main__":
    app.run()
