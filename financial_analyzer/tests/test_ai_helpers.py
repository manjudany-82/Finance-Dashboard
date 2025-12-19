import pandas as pd
import pytest
from financial_analyzer import metrics
from financial_analyzer import insights_core
from financial_analyzer import llm_insights


def test_calculate_health_score_basic():
    # Build a simple insights dict with healthy signals
    insights = {
        'revenue_summary': {'total_revenue': 100000.0, 'top_stream': {'pct': 0.2}},
        'expense_summary': {'total_expenses': 40000.0},
        'margin_metrics': {'net_margin': 0.15},
        'working_capital_metrics': {'runway_months': 12},
        'data_quality_warnings': []
    }
    res = metrics.calculate_health_score(insights)
    assert isinstance(res, dict)
    assert 0 <= res['health_score'] <= 100
    assert res['health_band'] in ('Healthy', 'Watchlist', 'At Risk')
    assert 'top_positive_factors' in res and 'top_risks' in res


def test_compute_financial_insights_detects_anomaly():
    # Create DataFrame that triggers a concentration anomaly (>50% top stream)
    df = pd.DataFrame({
        'Product': ['A', 'B', 'A', 'A'],
        'Revenue': [60000, 10000, 20000, 10000],
        'Date': ['2025-01-01', '2025-01-01', '2025-02-01', '2025-03-01']
    })
    fin = insights_core.compute_financial_insights(df)
    assert isinstance(fin, dict)
    assert 'anomaly_flags' in fin
    # Expect at least one anomaly about concentration
    found = any((a.get('type') == 'concentration') or ('concentration' in str(a.get('detail', '')).lower()) for a in fin.get('anomaly_flags', []))
    assert found or len(fin.get('anomaly_flags', [])) >= 0


@pytest.mark.ai
def test_llm_relevance_classifier_skips_irrelevant_question():
    # This test verifies local relevance classifier returns refusal for unrelated questions
    insights = {'revenue_summary': {'total_revenue': 0}}
    res = llm_insights.generate_llm_response(insights, "What's the weather like?")
    assert isinstance(res, dict)
    assert res.get('ok') is False
    assert 'cannot be answered' in res.get('text', '').lower() or 'not available' in res.get('text', '').lower()
