import pandas as pd
from financial_analyzer.analysis_modes import FinancialAnalyzer


def calculate_health_score(dfs):
    """Calculate overall business health score (0-100).

    Pure business logic: does not import Streamlit or any AI SDKs so tests
    can run in CI without secrets.
    """
    score = 100
    try:
        # Overview metrics
        ov = FinancialAnalyzer.analyze_overview(dfs)
        profit_margin = ov.get('net_profit_margin', 0)

        # Deduct points for poor profitability
        if profit_margin < 0:
            score -= 20
        elif profit_margin < 5:
            score -= 10

        # Cash flow analysis
        cash_res = FinancialAnalyzer.analyze_cash(dfs)
        runway = cash_res.get('runway_months', 999)
        if runway < 3:
            score -= 30
        elif runway < 6:
            score -= 15
        elif runway < 12:
            score -= 5

        # AR aging
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

        # Sales trend
        sales_res = FinancialAnalyzer.analyze_sales(dfs)
        trend = sales_res.get('trend', pd.DataFrame())
        if not trend.empty and len(trend) >= 3:
            recent_3 = trend.tail(3)['Revenue'].mean()
            prev_3 = trend.iloc[-6:-3]['Revenue'].mean() if len(trend) >= 6 else recent_3
            if recent_3 < prev_3 * 0.9:  # 10% decline
                score -= 10

    except Exception:
        pass

    return max(0, min(100, score))


def categorize_insights(all_insights, dfs):
    """Categorize all insights by priority: Critical, Important, Monitor.

    Kept pure so tests can import categorization logic without UI.
    """
    critical = []
    important = []
    monitor = []
    opportunities = []

    try:
        cash_res = FinancialAnalyzer.analyze_cash(dfs)
        runway = cash_res.get('runway_months', 999)

        ar_res = FinancialAnalyzer.analyze_ar(dfs)
        total_ar = ar_res.get('total_ar', 0)
        aging = ar_res.get('aging_table', pd.DataFrame())

        ov = FinancialAnalyzer.analyze_overview(dfs)
        profit_margin = ov.get('net_profit_margin', 0)

        for mode, insight_data in all_insights.items():
            bullets = insight_data.get('bullets', []) if isinstance(insight_data, dict) else insight_data
            for insight in bullets:
                insight_lower = insight.lower()
                if any(word in insight_lower for word in ['critical', 'urgent', 'alert', 'warning', 'low runway', 'overdue', 'loss']):
                    critical.append(f"[{mode}] {insight}")
                elif any(word in insight_lower for word in ['growing', 'up ', 'momentum', 'healthy', 'improving', 'positive']):
                    opportunities.append(f"[{mode}] {insight}")
                elif any(word in insight_lower for word in ['review', 'collections', 'cash need', 'burn', 'margin']):
                    important.append(f"[{mode}] {insight}")
                else:
                    monitor.append(f"[{mode}] {insight}")

        if runway < 6:
            critical.insert(0, f"[Cash] CRITICAL: Runway {runway:.1f} months - immediate action needed")

        if not aging.empty:
            old_debt = aging[aging['AgingBucket'].str.contains('60|90|Over', regex=True, na=False)]['Amount'].sum()
            if old_debt > 10000:
                critical.append(f"[Collections] ${old_debt:,.0f} overdue >60 days - escalate collections")

        if profit_margin < -10:
            critical.append(f"[Profitability] Operating loss {profit_margin:.1f}% - cost reduction urgent")

    except Exception as e:
        monitor.append(f"Analysis error: {str(e)}")

    return {
        'critical': critical[:5],
        'important': important[:7],
        'monitor': monitor[:8],
        'opportunities': opportunities[:5]
    }
