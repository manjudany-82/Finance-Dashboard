import pandas as pd


def compute_dashboard_insights(df: pd.DataFrame) -> dict:
    """Compute deterministic metrics and anomalies from the OneDrive DataFrame.

    This is extracted from dashboard.py so tests can import the pure business logic
    without pulling in Streamlit or any AI SDKs during pytest runs.
    """
    insights = {
        "revenue": {},
        "expenses": {},
        "profitability": {},
        "anomalies": [],
        "metadata": {
            "period": None,
            "source": "OneDrive Excel",
            "accounting_method": "Accrual"
        }
    }

    # Metadata
    insights["metadata"]["row_count"] = len(df)
    insights["metadata"]["columns"] = list(df.columns)

    # Heuristic detection of revenue/expense columns
    revenue_cols = [c for c in df.columns if any(k in c.lower() for k in ("revenue", "sales", "turnover"))]
    expense_cols = [c for c in df.columns if any(k in c.lower() for k in ("expense", "cost", "cogs", "fee", "fees"))]

    numeric = df.select_dtypes(include="number")

    # Revenue totals
    if revenue_cols:
        rev_totals = {c: float(df[c].sum()) for c in revenue_cols}
        total_revenue = sum(rev_totals.values())
    else:
        # fallback: pick numeric column with largest positive sum
        if not numeric.empty:
            sums = numeric.sum(numeric_only=True)
            candidate = sums[sums > 0]
            if not candidate.empty:
                top_col = candidate.idxmax()
                rev_totals = {top_col: float(candidate.max())}
                total_revenue = float(candidate.max())
            else:
                rev_totals = {}
                total_revenue = 0.0
        else:
            rev_totals = {}
            total_revenue = 0.0

    insights["revenue"]["totals"] = rev_totals
    insights["revenue"]["total_revenue"] = total_revenue

    # Top revenue stream
    if rev_totals:
        top_stream = max(rev_totals.items(), key=lambda x: x[1])
        insights["revenue"]["top_stream"] = {"name": top_stream[0], "value": top_stream[1], "pct": (top_stream[1] / total_revenue) if total_revenue else None}
    else:
        insights["revenue"]["top_stream"] = None

    # Expenses
    if expense_cols:
        exp_totals = {c: float(df[c].sum()) for c in expense_cols}
        total_expenses = sum(exp_totals.values())
    else:
        exp_totals = {}
        total_expenses = 0.0

    insights["expenses"]["totals"] = exp_totals
    insights["expenses"]["total_expenses"] = total_expenses

    # Profitability metrics
    insights["profitability"]["gross_margin"] = None
    insights["profitability"]["net_margin"] = None
    cogs_cols = [c for c in df.columns if "cog" in c.lower() or "cost of goods" in c.lower()]
    if cogs_cols and total_revenue:
        cogs = sum(float(df[c].sum()) for c in cogs_cols)
        gross = total_revenue - cogs
        insights["profitability"]["gross_margin"] = gross / total_revenue

    if total_revenue:
        net = total_revenue - total_expenses
        insights["profitability"]["net_margin"] = net / total_revenue

    # Anomalies detection (Python only)
    anomalies = []
    if insights["revenue"]["top_stream"] and insights["revenue"]["top_stream"]["pct"] is not None:
        if insights["revenue"]["top_stream"]["pct"] > 0.5:
            anomalies.append({"type": "concentration", "detail": f"Top revenue stream {insights['revenue']['top_stream']['name']} >50%"})

    for col, s in numeric.sum(numeric_only=True).items():
        if s == 0:
            anomalies.append({"type": "zero_total", "detail": f"Column {col} sums to zero"})
        if s < 0:
            anomalies.append({"type": "negative_total", "detail": f"Column {col} has negative total: {s}"})

    mgmt_cols = [c for c in df.columns if "management fee" in c.lower() or "management" in c.lower()]
    if mgmt_cols and total_revenue:
        mgmt_total = sum(float(df[c].sum()) for c in mgmt_cols)
        if mgmt_total > 0.2 * total_revenue:
            anomalies.append({"type": "high_fixed_cost", "detail": f"Management fees {mgmt_total} exceed 20% of revenue"})

    insights["anomalies"] = anomalies

    # Period detection (best-effort)
    if any("date" in c.lower() for c in df.columns):
        try:
            date_col = next(c for c in df.columns if "date" in c.lower())
            min_d = pd.to_datetime(df[date_col], errors="coerce").min()
            max_d = pd.to_datetime(df[date_col], errors="coerce").max()
            insights["metadata"]["period"] = f"{min_d} to {max_d}"
        except Exception:
            insights["metadata"]["period"] = None

    return insights
