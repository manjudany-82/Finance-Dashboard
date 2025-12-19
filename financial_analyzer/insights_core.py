import json
import pandas as pd
from typing import Dict, Any
from financial_analyzer import metrics as _metrics
from financial_analyzer.analysis_modes import FinancialAnalyzer


def compute_financial_insights(df: pd.DataFrame) -> Dict[str, Any]:
    """Compute structured, deterministic financial insights from OneDrive Excel.

    Returns a dict with strict data boundaries suitable for passing to an LLM
    for interpretation only. All numbers are computed in Python.

    Keys:
      - revenue_summary
      - expense_summary
      - margin_metrics
      - working_capital_metrics
      - anomaly_flags
      - data_quality_warnings
    """
    if df is None or getattr(df, 'empty', True):
        return {
            'revenue_summary': {},
            'expense_summary': {},
            'margin_metrics': {},
            'working_capital_metrics': {},
            'anomaly_flags': [],
            'data_quality_warnings': ['No OneDrive data loaded']
        }

    # Start from the deterministic dashboard computation
    base = _metrics.compute_dashboard_insights(df)

    # Revenue summary
    revenue = {
        'totals': base.get('revenue', {}).get('totals', {}),
        'total_revenue': base.get('revenue', {}).get('total_revenue', 0.0),
        'top_stream': base.get('revenue', {}).get('top_stream')
    }

    # Expense summary
    expenses = {
        'totals': base.get('expenses', {}).get('totals', {}),
        'total_expenses': base.get('expenses', {}).get('total_expenses', 0.0)
    }

    # Margin metrics
    margin_metrics = {
        'gross_margin': base.get('profitability', {}).get('gross_margin'),
        'net_margin': base.get('profitability', {}).get('net_margin')
    }

    # Working capital metrics (best-effort from FinancialAnalyzer)
    try:
        ar = FinancialAnalyzer.analyze_ar(df) or {}
        ap = FinancialAnalyzer.analyze_ap(df) or {}
        cash = FinancialAnalyzer.analyze_cash(df) or {}
        working_capital = {
            'total_ar': ar.get('total_ar'),
            'aging_table_present': (False if ar.get('aging_table') is None else not ar.get('aging_table').empty),
            'total_ap': ap.get('total_open'),
            'upcoming_payables_30d': ap.get('upcoming_30d'),
            'cash_balance': cash.get('current_balance'),
            'runway_months': cash.get('runway_months')
        }
    except Exception:
        working_capital = {}

    # Anomaly flags (rule-based)
    anomaly_flags = base.get('anomalies', []) or []

    # Data quality warnings
    warnings = base.get('metadata', {}).get('warnings') if isinstance(base.get('metadata', {}), dict) else None
    # Fallback to simple checks
    data_quality_warnings = []
    cols = [c.lower() for c in df.columns]
    if not any('date' in c for c in cols):
        data_quality_warnings.append('No date column detected — prior-period comparisons unavailable')
    if not any('ar' in c or 'receivable' in c for c in cols):
        data_quality_warnings.append('Accounts Receivable (AR) data missing or incomplete')
    if not any('ap' in c or 'payable' in c for c in cols):
        data_quality_warnings.append('Accounts Payable (AP) data missing or incomplete')
    if not any('cog' in c or 'cost of goods' in c for c in cols):
        data_quality_warnings.append('COGS not present — gross margin calculations may be incomplete')

    # Merge any warnings from base metadata
    if warnings:
        if isinstance(warnings, list):
            data_quality_warnings.extend(warnings)
        elif isinstance(warnings, str):
            data_quality_warnings.append(warnings)

    # Trim duplicates
    data_quality_warnings = list(dict.fromkeys([w for w in data_quality_warnings if w]))

    return {
        'revenue_summary': revenue,
        'expense_summary': expenses,
        'margin_metrics': margin_metrics,
        'working_capital_metrics': working_capital,
        'anomaly_flags': anomaly_flags,
        'data_quality_warnings': data_quality_warnings,
        'raw_metadata': base.get('metadata', {})
    }


def calculate_health_score(dfs) -> int:
    """Compatibility wrapper: compute integer health score (0-100) using
    FinancialAnalyzer heuristics. Preserves previous behavior so tests
    importing this symbol from `insights_core` continue to work.
    """
    score = 100
    try:
        ov = FinancialAnalyzer.analyze_overview(dfs)
        profit_margin = ov.get('net_profit_margin', 0)

        if profit_margin < 0:
            score -= 20
        elif profit_margin < 5:
            score -= 10

        cash_res = FinancialAnalyzer.analyze_cash(dfs)
        runway = cash_res.get('runway_months', 999)
        if runway < 3:
            score -= 30
        elif runway < 6:
            score -= 15
        elif runway < 12:
            score -= 5

        ar_res = FinancialAnalyzer.analyze_ar(dfs)
        aging = ar_res.get('aging_table', pd.DataFrame())
        if not aging.empty:
            old_debt = aging[aging['AgingBucket'].str.contains('60|90|Over', regex=True, na=False)]['Amount'].sum()
            total_ar = ar_res.get('total_ar', 1)
            if total_ar > 0:
                old_pct = (old_debt / total_ar) * 100
                if old_pct > 30:
                    score -= 15
                elif old_pct > 15:
                    score -= 8

        sales_res = FinancialAnalyzer.analyze_sales(dfs)
        trend = sales_res.get('trend', pd.DataFrame())
        if not trend.empty and len(trend) >= 3:
            recent_3 = trend.tail(3)['Revenue'].mean()
            prev_3 = trend.iloc[-6:-3]['Revenue'].mean() if len(trend) >= 6 else recent_3
            if recent_3 < prev_3 * 0.9:
                score -= 10
    except Exception:
        pass

    return max(0, min(100, score))


def categorize_insights(all_insights, dfs):
    """Keep existing categorization helper but delegate to metrics if available."""
    try:
        # reuse previous categorization heuristic if present in metrics
        return _metrics.categorize_insights(all_insights, dfs)
    except Exception:
        # fallback simple categorization
        critical = [i for i in (all_insights or {}).get('anomalies', [])][:5]
        return {'critical': critical, 'important': [], 'monitor': [], 'opportunities': []}
