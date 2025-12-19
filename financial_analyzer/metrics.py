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


def calculate_health_score(insights_dict: dict) -> dict:
    """Deterministic Business Health Score (0-100) based on insights_dict.

    Inputs (expected keys in insights_dict):
      - revenue_summary.total_revenue
      - revenue_summary.top_stream.pct
      - expense_summary.total_expenses
      - margin_metrics.net_margin
      - working_capital_metrics.runway_months
      - data_quality_warnings (list)

    Returns dict with:
      - health_score (int)
      - health_band (str)
      - top_positive_factors (list)
      - top_risks (list)
    """
    # Defaults
    score = 0.0
    positive = []
    risks = []

    rev = insights_dict.get('revenue_summary', {}) or {}
    exp = insights_dict.get('expense_summary', {}) or {}
    margin = insights_dict.get('margin_metrics', {}) or {}
    wc = insights_dict.get('working_capital_metrics', {}) or {}
    warnings = insights_dict.get('data_quality_warnings', []) or []

    # Profitability (30%) - use net_margin as percent (e.g., 0.1 -> 10)
    net_margin = margin.get('net_margin') if margin else None
    if net_margin is None:
        profit_score = 50.0
    else:
        try:
            profit_pct = float(net_margin) * 100
        except Exception:
            profit_pct = float(net_margin or 0)
        # Map profit % to 0..100 (clamped): 20%+ ->100, 0% ->50, negative ->0
        if profit_pct >= 20:
            profit_score = 100.0
        elif profit_pct <= 0:
            profit_score = max(0.0, 50.0 + profit_pct * 2.5)  # negative reduces below 50
        else:
            profit_score = 50.0 + (profit_pct / 20.0) * 50.0
    score += 0.30 * profit_score
    if profit_score > 70:
        positive.append(f"Net margin {profit_pct:.1f}%")
    if profit_score < 40:
        risks.append(f"Low net margin {profit_pct:.1f}%")

    # Revenue stability / concentration (20%) - penalize concentration
    top = rev.get('top_stream') or {}
    top_pct = top.get('pct') if isinstance(top, dict) else None
    try:
        top_pct = float(top_pct) if top_pct is not None else 0.0
    except Exception:
        top_pct = 0.0
    # If top_pct > 50% -> low stability
    if top_pct >= 0.5:
        rev_score = 20.0
        risks.append('High revenue concentration')
    else:
        rev_score = 100.0 - (top_pct * 100.0)  # more evenly distributed => higher
        if rev_score > 70:
            positive.append('Diverse revenue streams')
    score += 0.20 * rev_score

    # Expense discipline (20%) - lower expense/revenue ratio -> better
    total_rev = float(rev.get('total_revenue') or 0.0)
    total_exp = float(exp.get('total_expenses') or 0.0)
    if total_rev > 0:
        exp_ratio = total_exp / total_rev
        # Map: exp_ratio 0.0 -> 100, 0.8 ->50, >1 ->0
        if exp_ratio <= 0.2:
            exp_score = 100.0
        elif exp_ratio >= 1.0:
            exp_score = 0.0
        else:
            exp_score = max(0.0, 100.0 - ((exp_ratio - 0.2) / 0.8) * 100.0)
    else:
        exp_score = 50.0
    score += 0.20 * exp_score
    if exp_score > 70:
        positive.append('Controlled expense profile')
    if exp_score < 40:
        risks.append('High expense ratio')

    # Liquidity (20%) - runway mapping
    runway = wc.get('runway_months')
    try:
        runway = float(runway) if runway is not None else None
    except Exception:
        runway = None
    if runway is None:
        liq_score = 50.0
    else:
        if runway >= 12:
            liq_score = 100.0
        elif runway >= 6:
            liq_score = 80.0
        elif runway >= 3:
            liq_score = 50.0
        else:
            liq_score = 10.0
    score += 0.20 * liq_score
    if liq_score >= 80:
        positive.append(f"Runway {runway:.1f} months")
    if liq_score < 40:
        risks.append(f"Low runway {runway:.1f} months")

    # Data quality confidence (10%) - fewer warnings -> higher
    warnings_count = len(warnings) if warnings else 0
    # Map: 0 warnings -> 100, 3+ warnings -> 20
    if warnings_count == 0:
        dq_score = 100.0
    elif warnings_count >= 3:
        dq_score = 20.0
    else:
        dq_score = 100.0 - (warnings_count / 3.0) * 80.0
    score += 0.10 * dq_score
    if dq_score > 70:
        positive.append('High data confidence')
    if dq_score < 40:
        risks.append('Low data confidence')

    final = int(max(0, min(100, round(score))))

    if final >= 80:
        band = 'Healthy'
    elif final >= 60:
        band = 'Watchlist'
    else:
        band = 'At Risk'

    # Top factors: choose up to 3 positives and top 3 risks
    top_positive = positive[:3]
    top_risks = risks[:3]

    return {
        'health_score': final,
        'health_band': band,
        'top_positive_factors': top_positive,
        'top_risks': top_risks
    }


def calculate_health_score_v2(df: pd.DataFrame) -> dict:
    """Deterministic, explainable health score v2 computed from raw DataFrame.

    Returns structure:
    {
      'score': int,
      'band': str,
      'components': { 'revenue_trend': {...}, 'profitability': {...}, 'cash_stability': {...}, 'volatility': {...} },
      'positives': [...],
      'risks': [...]
    }
    """
    # Default low-result for missing input
    result = {
        'score': 0,
        'band': 'At Risk',
        'components': {
            'revenue_trend': {'score': 0, 'note': 'Insufficient revenue data'},
            'profitability': {'score': 0, 'note': 'Insufficient P&L data'},
            'cash_stability': {'score': 0, 'note': 'No cash/balance series'},
            'volatility': {'score': 0, 'note': 'Insufficient data for volatility'}
        },
        'positives': [],
        'risks': []
    }

    if df is None or getattr(df, 'empty', True):
        result['risks'].append('No accounting data')
        return result

    # Identify date and revenue columns
    cols = [c.lower() for c in df.columns]
    date_col = None
    for c in df.columns:
        if 'date' in c.lower():
            date_col = c
            break

    # revenue column detection (heuristic)
    revenue_col = None
    for c in df.columns:
        if any(k in c.lower() for k in ('revenue', 'sales', 'amount', 'turnover')) and pd.api.types.is_numeric_dtype(df[c]):
            revenue_col = c
            break

    # expenses detection
    expense_col = None
    for c in df.columns:
        if any(k in c.lower() for k in ('expense', 'cost', 'cogs', 'spend')) and pd.api.types.is_numeric_dtype(df[c]):
            expense_col = c
            break

    # cash / balance detection
    cash_col = None
    for c in df.columns:
        if any(k in c.lower() for k in ('cash', 'balance', 'bank', 'current_balance')) and pd.api.types.is_numeric_dtype(df[c]):
            cash_col = c
            break

    positives = []
    risks = []

    # Revenue trend component (30%)
    rev_score = 0
    rev_note = ''
    if revenue_col is None:
        rev_note = 'Revenue column missing'
        risks.append(rev_note)
    else:
        try:
            if date_col:
                tmp = df[[date_col, revenue_col]].dropna()
                tmp[date_col] = pd.to_datetime(tmp[date_col], errors='coerce')
                tmp = tmp.dropna(subset=[date_col])
                if tmp.empty or len(tmp) < 4:
                    # insufficient time series
                    rev_note = 'Insufficient revenue time series'
                    rev_score = 40
                    risks.append(rev_note)
                else:
                    tmp = tmp.set_index(date_col).resample('M').sum()
                    rev_ts = tmp[revenue_col]
                    # compare recent 3 months vs prior 3 months
                    if len(rev_ts) >= 6:
                        recent = rev_ts[-3:].mean()
                        prior = rev_ts[-6:-3].mean()
                        if prior <= 0:
                            pct = 0.0
                        else:
                            pct = (recent - prior) / prior * 100.0
                        # map pct to 0..100 where >=10% ->100, 0% ->50, -10% ->0
                        if pct >= 10:
                            rev_score = 100
                            rev_note = f'Revenue growing {pct:.1f}% vs prior period'
                            positives.append(rev_note)
                        elif pct <= -10:
                            rev_score = 0
                            rev_note = f'Revenue declining {pct:.1f}% vs prior period'
                            risks.append(rev_note)
                        else:
                            rev_score = int(50 + (pct / 10.0) * 50)
                            rev_note = f'Revenue change {pct:.1f}% vs prior period'
                    else:
                        # fallback: use slope of linear regression on months
                        s = rev_ts.dropna()
                        if len(s) >= 3:
                            x = range(len(s))
                            coeff = (pd.Series(s).iloc[-1] - pd.Series(s).iloc[0]) / max(1, len(s)-1)
                            pct = (coeff / (pd.Series(s).mean() if pd.Series(s).mean() else 1)) * 100
                            if pct >= 5:
                                rev_score = 85
                                positives.append('Revenue trending upward')
                                rev_note = 'Revenue trending upward'
                            elif pct <= -5:
                                rev_score = 20
                                risks.append('Revenue trending downward')
                                rev_note = 'Revenue trending downward'
                            else:
                                rev_score = 50
                                rev_note = 'Revenue stable'
                        else:
                            rev_score = 45
                            rev_note = 'Limited revenue data'
        except Exception:
            rev_score = 40
            rev_note = 'Error computing revenue trend'
            risks.append(rev_note)

    result['components']['revenue_trend'] = {'score': int(max(0, min(100, rev_score))), 'note': rev_note}

    # Profitability component (30%)
    prof_score = 0
    prof_note = ''
    if revenue_col is None or expense_col is None:
        prof_note = 'Revenue or expense column missing'
        prof_score = 35
        risks.append(prof_note)
    else:
        try:
            total_rev = float(df[revenue_col].sum())
            total_exp = float(df[expense_col].sum())
            if total_rev == 0:
                prof_score = 30
                prof_note = 'Zero revenue total'
                risks.append(prof_note)
            else:
                net_margin = (total_rev - total_exp) / total_rev * 100.0
                # Map margin: >=20% ->100, 0% ->50, -20% ->0
                if net_margin >= 20:
                    prof_score = 100
                    positives.append(f'Net margin {net_margin:.1f}%')
                    prof_note = f'Net margin {net_margin:.1f}%' 
                elif net_margin <= -20:
                    prof_score = 0
                    risks.append(f'Net loss {net_margin:.1f}%')
                    prof_note = f'Net loss {net_margin:.1f}%' 
                else:
                    prof_score = int(max(0, min(100, 50 + (net_margin / 20.0) * 50)))
                    prof_note = f'Net margin {net_margin:.1f}%'
        except Exception:
            prof_score = 35
            prof_note = 'Error computing profitability'
            risks.append(prof_note)

    result['components']['profitability'] = {'score': int(max(0, min(100, prof_score))), 'note': prof_note}

    # Cash stability (20%)
    cash_score = 0
    cash_note = ''
    if cash_col is None:
        cash_note = 'No cash/balance column'
        cash_score = 30
        risks.append(cash_note)
    else:
        try:
            series = df[cash_col].dropna().astype(float)
            if series.empty:
                cash_score = 30
                cash_note = 'No cash observations'
                risks.append(cash_note)
            else:
                mean = series.mean()
                sd = series.std() if len(series) > 1 else 0.0
                cv = abs(sd / mean) if mean != 0 else float('inf')
                # scoring: mean positive and low cv => high
                if mean >= 0 and cv <= 0.2:
                    cash_score = 100
                    cash_note = f'Cash positive (mean ${mean:,.0f}) stable'
                    positives.append(cash_note)
                elif mean >= 0 and cv <= 0.5:
                    cash_score = 70
                    cash_note = f'Cash positive but variable (cv {cv:.2f})'
                elif mean >= 0:
                    cash_score = 50
                    cash_note = 'Cash positive but volatile'
                else:
                    cash_score = 10
                    cash_note = f'Cash negative (mean ${mean:,.0f})'
                    risks.append(cash_note)
        except Exception:
            cash_score = 30
            cash_note = 'Error computing cash stability'
            risks.append(cash_note)

    result['components']['cash_stability'] = {'score': int(max(0, min(100, cash_score))), 'note': cash_note}

    # Volatility (20%) - penalize large month-to-month swings in revenue
    vol_score = 0
    vol_note = ''
    if revenue_col is None or date_col is None:
        vol_note = 'Insufficient revenue/time data for volatility'
        vol_score = 40
        risks.append(vol_note)
    else:
        try:
            tmp = df[[date_col, revenue_col]].dropna()
            tmp[date_col] = pd.to_datetime(tmp[date_col], errors='coerce')
            tmp = tmp.dropna(subset=[date_col])
            ts = tmp.set_index(date_col).resample('M').sum()[revenue_col]
            if ts.empty or len(ts) < 3:
                vol_score = 50
                vol_note = 'Insufficient series for volatility'
            else:
                pct = ts.pct_change().dropna()
                if pct.empty:
                    vol_score = 80
                    vol_note = 'Low volatility'
                else:
                    mad = pct.abs().mean() * 100.0
                    # map mad: <=5% ->100, >=30% ->0
                    if mad <= 5:
                        vol_score = 100
                        vol_note = f'Low revenue volatility ({mad:.1f}% avg MoM)'
                        positives.append(vol_note)
                    elif mad >= 30:
                        vol_score = 0
                        vol_note = f'High revenue volatility ({mad:.1f}% avg MoM)'
                        risks.append(vol_note)
                    else:
                        vol_score = int(max(0, min(100, 100 - ((mad - 5) / (30 - 5)) * 100)))
                        vol_note = f'Revenue volatility {mad:.1f}% avg MoM'
        except Exception:
            vol_score = 40
            vol_note = 'Error computing volatility'
            risks.append(vol_note)

    result['components']['volatility'] = {'score': int(max(0, min(100, vol_score))), 'note': vol_note}

    # Weighted aggregation
    final = (
        0.30 * result['components']['revenue_trend']['score'] +
        0.30 * result['components']['profitability']['score'] +
        0.20 * result['components']['cash_stability']['score'] +
        0.20 * result['components']['volatility']['score']
    )
    final_score = int(max(0, min(100, round(final))))

    # Banding
    if final_score >= 85:
        band = 'Excellent'
    elif final_score >= 75:
        band = 'Healthy'
    elif final_score >= 60:
        band = 'Watch'
    else:
        band = 'At Risk'

    result['score'] = final_score
    result['band'] = band
    result['positives'] = positives[:5]
    result['risks'] = risks[:5]

    return result
