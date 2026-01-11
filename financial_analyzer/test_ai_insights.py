import pandas as pd
import pytest

from dashboard import compute_dashboard_insights
from financial_analyzer.llm_insights import calculate_health_score


def test_compute_dashboard_insights_basic():
    df = pd.DataFrame({
        'Date': pd.date_range('2025-01-01', periods=4, freq='M'),
        'Product': ['A', 'A', 'B', 'B'],
        'Revenue': [100, 150, 200, 50],
        'COGS': [40, 60, 80, 20],
        'Management Fee': [10, 10, 10, 10],
    })

    insights = compute_dashboard_insights(df)

    assert isinstance(insights, dict)
    assert 'revenue' in insights
    assert insights['revenue']['total_revenue'] == 500
    assert insights['revenue']['totals']  # per-column totals present
    assert 'profitability' in insights
    assert 'anomalies' in insights


def test_calculate_health_score_rules(monkeypatch):
    # Patch FinancialAnalyzer helpers to produce deterministic conditions
    from financial_analyzer import analysis_modes

    monkeypatch.setattr(analysis_modes.FinancialAnalyzer, 'analyze_overview', staticmethod(lambda dfs: {'net_profit_margin': -5}))
    monkeypatch.setattr(analysis_modes.FinancialAnalyzer, 'analyze_cash', staticmethod(lambda dfs: {'runway_months': 2}))
    # AR aging: make >30% overdue
    aging = pd.DataFrame({'AgingBucket': ['Current', '60-90', '90+'], 'Amount': [20, 30, 50]})
    monkeypatch.setattr(analysis_modes.FinancialAnalyzer, 'analyze_ar', staticmethod(lambda dfs: {'aging_table': aging, 'total_ar': 100}))

    # Sales trend triggers recent decline (so -10)
    trend = pd.DataFrame({'Month': pd.date_range('2025-01-01', periods=6, freq='M'), 'Revenue': [200, 200, 200, 150, 150, 100]})
    monkeypatch.setattr(analysis_modes.FinancialAnalyzer, 'analyze_sales', staticmethod(lambda dfs: {'trend': trend}))

    score = calculate_health_score(None)

    # Explanation of expected deductions:
    # start 100
    # profit_margin < 0 => -20 -> 80
    # runway < 3 => -30 -> 50
    # AR overdue >30% => -15 -> 35
    # sales decline => -10 -> 25
    assert score == 25
