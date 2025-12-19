import pandas as pd
from financial_analyzer.metrics import calculate_health_score_v2


def make_monthly_df(start='2024-01-01', months=12, revenue_series=None, expense_series=None, cash_series=None):
    dates = pd.date_range(start, periods=months, freq='MS')
    if revenue_series is None:
        revenue_series = [1000 + i * 50 for i in range(months)]
    if expense_series is None:
        expense_series = [600 + i * 10 for i in range(months)]
    if cash_series is None:
        cash_series = [500 + i * 20 for i in range(months)]
    df = pd.DataFrame({'date': dates, 'revenue': revenue_series, 'expense': expense_series, 'cash_balance': cash_series})
    return df


def test_v2_stable_growing_business():
    # revenue grows steadily, margins healthy, cash stable => expect score >= 75 (Healthy/Excellent)
    df = make_monthly_df()
    out = calculate_health_score_v2(df)
    assert isinstance(out, dict)
    assert out['score'] >= 75, f"Expected >=75 for stable growing business, got {out['score']}"


def test_v2_declining_volatile_business():
    # revenue declines and is volatile, margins negative, cash negative => expect score <= 50
    months = 12
    rev = [1200 - i * 150 + ((-1) ** i) * 200 for i in range(months)]
    exp = [1000 + i * 50 for i in range(months)]
    cash = [300 - i * 50 for i in range(months)]
    df = make_monthly_df(revenue_series=rev, expense_series=exp, cash_series=cash)
    out = calculate_health_score_v2(df)
    assert isinstance(out, dict)
    assert out['score'] <= 50, f"Expected <=50 for declining/volatile business, got {out['score']}"
