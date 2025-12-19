"""
AI Business Insights Tab - Consolidated Executive Intelligence
Provides comprehensive AI-powered analysis across all financial areas
"""

import streamlit as st
import pandas as pd
import json
import hashlib
from financial_analyzer.analysis_modes import FinancialAnalyzer
from financial_analyzer.render_layouts import _get_batched_insights

try:
    from google import genai
except Exception:
    genai = None


MONTH_NAME_MAP = {
    'jan': 1, 'january': 1,
    'feb': 2, 'february': 2,
    'mar': 3, 'march': 3,
    'apr': 4, 'april': 4,
    'may': 5,
    'jun': 6, 'june': 6,
    'jul': 7, 'july': 7,
    'aug': 8, 'august': 8,
    'sep': 9, 'sept': 9, 'september': 9,
    'oct': 10, 'october': 10,
    'nov': 11, 'november': 11,
    'dec': 12, 'december': 12
}


def _extract_month_filters(question: str):
    """Extract month numbers mentioned in the question for filtering."""
    q = question.lower()
    months = {num for name, num in MONTH_NAME_MAP.items() if name in q}
    return list(months)


def _detect_product_filters(question: str, available_products):
    """Match product names mentioned in the question against known products."""
    q = question.lower()
    return [p for p in available_products if isinstance(p, str) and p.lower() in q]


def _detect_intents(question: str):
    """Rule-based intent detection to decide which tables to retrieve."""
    q = question.lower()
    intent_map = {
        'revenue': ['revenue', 'sales', 'top line', 'growth', 'mom', 'trend', 'product'],
        'anomaly': ['anomaly', 'spike', 'drop', 'swing', 'volatility', 'outlier'],
        'cash': ['cash', 'runway', 'burn', 'liquidity', 'balance'],
        'ar': ['ar', 'receivable', 'collections'],
        'ap': ['ap', 'payable', 'vendor'],
        'profit': ['profit', 'margin', 'ebitda', 'net'],
        'expense': ['expense', 'spend', 'cost', 'opex'],
        'forecast': ['forecast', 'project', 'projection', 'next']
    }

    intents = {name for name, keys in intent_map.items() if any(k in q for k in keys)}
    if not intents:
        intents = {'revenue', 'profit'}
    return intents


def _format_month(val):
    try:
        return pd.to_datetime(val).strftime('%b %Y')
    except Exception:
        return str(val)


def _summarize_sales(sales_res, months_filter, products_filter):
    trend = sales_res.get('trend', pd.DataFrame())
    product_monthly = sales_res.get('product_monthly', pd.DataFrame())
    summary_parts = []

    if not trend.empty:
        tmp = trend.copy()
        tmp['Month'] = pd.to_datetime(tmp['Month'], errors='coerce')
        tmp = tmp.dropna(subset=['Month'])
        if months_filter:
            tmp = tmp[tmp['Month'].dt.month.isin(months_filter)]
        tmp = tmp.sort_values('Month').tail(3)
        if not tmp.empty:
            rev_bits = [f"{row['Month'].strftime('%b %Y')}: ${row['Revenue']:,.0f}" for _, row in tmp.iterrows()]
            summary_parts.append("Revenue trend: " + '; '.join(rev_bits))

    if not product_monthly.empty:
        pm = product_monthly.copy()
        pm.columns = pd.to_datetime(pm.columns, errors='coerce')
        pm = pm.loc[:, pm.columns.notnull()]
        if pm.empty:
            return ' '.join(summary_parts)
        if products_filter:
            pm = pm[pm.index.isin(products_filter)]
        top_products = pm.sum(axis=1).nlargest(3)
        prod_bits = []
        for name, total in top_products.items():
            latest_month = pm.columns.max()
            if pd.isna(latest_month):
                continue
            latest_val = pm.loc[name, latest_month]
            prod_bits.append(f"{name}: ${latest_val:,.0f} latest; YTD ${total:,.0f}")
        if prod_bits:
            summary_parts.append("Products: " + '; '.join(prod_bits))

    return ' '.join(summary_parts)


def _summarize_anomalies(dfs, months_filter, products_filter):
    anomalies = FinancialAnalyzer.detect_anomalies(dfs)
    if anomalies.empty:
        return ""
    df = anomalies.copy()
    if months_filter:
        month_labels = {_format_month(pd.Timestamp(month=mn, day=1, year=2000))[:3] for mn in months_filter}
        df = df[df['Month'].str[:3].isin(month_labels)]
    if products_filter:
        df = df[df['Product'].isin(products_filter)]
    if df.empty:
        return ""
    df = df.head(5)
    lines = []
    for _, row in df.iterrows():
        try:
            growth = float(row['MoM_Growth_Pct'])
            growth_txt = f"{growth:+.1f}%"
        except Exception:
            growth_txt = str(row.get('MoM_Growth_Pct', ''))
        lines.append(
            f"{row['Product']} {row['Month']}: {row['Anomaly_Type']} {growth_txt} (${row['Revenue']:,.0f})"
        )
    return "Anomalies: " + '; '.join(lines)


def _summarize_profitability(profit_res, months_filter):
    if not profit_res:
        return ""
    metrics = profit_res.get('metrics', {})
    pnl = profit_res.get('monthly_pnl', pd.DataFrame())
    net_margin = metrics.get('net_margin')
    op_margin = metrics.get('op_margin')
    net_profit = metrics.get('ytd_net_profit')
    pieces = []
    if net_margin is not None:
        pieces.append(f"Net margin {net_margin:.1f}% YTD")
    if op_margin is not None:
        pieces.append(f"Operating margin {op_margin:.1f}% YTD")
    if net_profit is not None:
        pieces.append(f"YTD net profit ${net_profit:,.0f}")

    if pnl is not None and not pnl.empty:
        df = pnl.copy()
        df['Month'] = pd.to_datetime(df['Month'], errors='coerce')
        df = df.dropna(subset=['Month']).sort_values('Month')
        if months_filter:
            df = df[df['Month'].dt.month.isin(months_filter)]
        if not df.empty:
            last = df.iloc[-1]
            pieces.append(
                f"Latest {_format_month(last['Month'])}: net ${last['NetProfit']:,.0f}, margin {last['Margin']:.1f}%"
            )

    return ' | '.join(pieces)


def _summarize_cash(cash_res):
    if not cash_res:
        return ""
    runway = cash_res.get('runway_months')
    balance = cash_res.get('current_balance')
    burn = cash_res.get('burn_rate_mo')
    parts = []
    if balance is not None:
        parts.append(f"Cash balance ${balance:,.0f}")
    if runway is not None:
        parts.append(f"Runway {runway:.1f} months" if runway < 999 else "Runway stable")
    if burn is not None and burn > 0:
        parts.append(f"Burn ${burn:,.0f}/month")
    return ' | '.join(parts)


def _summarize_ar(ar_res):
    if not ar_res:
        return ""
    total_ar = ar_res.get('total_ar', 0)
    aging = ar_res.get('aging_table', pd.DataFrame())
    overdue = 0
    if aging is not None and not aging.empty:
        overdue = aging[aging['AgingBucket'].str.contains('60|90|Over', regex=True, na=False)]['Amount'].sum()
    return f"AR ${total_ar:,.0f}; Overdue >60d ${overdue:,.0f}" if total_ar or overdue else ""


def _summarize_ap(ap_res):
    if not ap_res:
        return ""
    total_open = ap_res.get('total_open', 0)
    upcoming = ap_res.get('upcoming_30d', 0)
    if not total_open and not upcoming:
        return ""
    return f"AP ${total_open:,.0f}; due next 30d ${upcoming:,.0f}"


def _summarize_spending(spending_res, months_filter):
    if not spending_res:
        return ""
    monthly = spending_res.get('monthly', pd.DataFrame())
    top_5 = spending_res.get('top_5_ytd', pd.DataFrame())
    bits = []
    if monthly is not None and not monthly.empty:
        df = monthly.copy()
        df['Month'] = pd.to_datetime(df['Month'], errors='coerce')
        df = df.dropna(subset=['Month']).sort_values('Month')
        if months_filter:
            df = df[df['Month'].dt.month.isin(months_filter)]
        if not df.empty:
            last = df.iloc[-1]
            bits.append(f"Expenses {_format_month(last['Month'])}: ${last['Revenue']:,.0f}")
    if top_5 is not None and not top_5.empty:
        names = [f"{row.Product}: ${row.Revenue:,.0f}" for row in top_5.itertuples()][:3]
        if names:
            bits.append("Top expense drivers: " + '; '.join(names))
    return ' | '.join(bits)


def _build_structured_context(dfs, question: str):
    intents = _detect_intents(question)
    months_filter = _extract_month_filters(question)
    sales_res = FinancialAnalyzer.analyze_sales(dfs)
    available_products = sales_res.get('by_product', pd.DataFrame())
    product_names = available_products['Product'].tolist() if available_products is not None and not available_products.empty else []
    products_filter = _detect_product_filters(question, product_names)

    context_parts = []

    overview = FinancialAnalyzer.analyze_overview(dfs)
    if overview:
        context_parts.append(
            f"Overview: YTD sales ${overview.get('ytd_sales', 0):,.0f}; expenses ${overview.get('ytd_expense', 0):,.0f}; net profit ${overview.get('net_profit', 0):,.0f}; net margin {overview.get('net_profit_margin', 0):.1f}%"
        )

    if 'revenue' in intents:
        sales_summary = _summarize_sales(sales_res, months_filter, products_filter)
        if sales_summary:
            context_parts.append(sales_summary)

    if 'anomaly' in intents:
        anomaly_summary = _summarize_anomalies(dfs, months_filter, products_filter)
        if anomaly_summary:
            context_parts.append(anomaly_summary)

    if 'cash' in intents:
        cash_summary = _summarize_cash(FinancialAnalyzer.analyze_cash(dfs))
        if cash_summary:
            context_parts.append(cash_summary)

    if 'ar' in intents:
        ar_summary = _summarize_ar(FinancialAnalyzer.analyze_ar(dfs))
        if ar_summary:
            context_parts.append(ar_summary)

    if 'ap' in intents:
        ap_summary = _summarize_ap(FinancialAnalyzer.analyze_ap(dfs))
        if ap_summary:
            context_parts.append(ap_summary)

    if 'profit' in intents:
        profit_summary = _summarize_profitability(FinancialAnalyzer.analyze_profit(dfs), months_filter)
        if profit_summary:
            context_parts.append("Profitability: " + profit_summary)

    if 'expense' in intents:
        spending_summary = _summarize_spending(FinancialAnalyzer.analyze_spending(dfs), months_filter)
        if spending_summary:
            context_parts.append(spending_summary)

    return '\n'.join([c for c in context_parts if c]).strip()


def _df_fingerprint(df: pd.DataFrame) -> str:
    """Create a light fingerprint for caching: cols + shape + numeric sums."""
    try:
        cols = '|'.join(map(str, df.columns.tolist()))
        shape = f"{df.shape[0]}x{df.shape[1]}"
        numeric = df.select_dtypes(include='number')
        sums = ''
        if not numeric.empty:
            sums = '|'.join([f"{c}:{round(float(numeric[c].sum()),2)}" for c in numeric.columns])
        base = f"{cols}||{shape}||{sums}"
        return hashlib.sha256(base.encode('utf-8')).hexdigest()
    except Exception:
        return ''


def _generate_grounded_answer(ai, question: str, context_text: str):
    """Send grounded context to Gemini with strict hallucination guardrails."""
    if not context_text:
        return "Not enough data available."
    if genai is None or ai is None or not getattr(ai, 'api_key', None):
        return "Not enough data available."

    prompt = (
        "You are a CFO decision-support assistant. "
        "Answer ONLY using the provided financial data. "
        "If data is insufficient, respond with: 'Not enough data available.' "
        "Keep answers concise (<=120 words), executive-friendly, and reference specific months, products, or KPIs. "
        "Explain causes only when the context hints at them (e.g., low base, expense overruns).\n\n"
        f"Question: {question.strip()}\n"
        f"Financial data context:\n{context_text}\n"
    )

    try:
        genai.configure(api_key=getattr(ai, 'api_key', None))
        model_name = getattr(ai, 'preferred_model', 'gemini-1.5-flash') or 'gemini-1.5-flash'
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(prompt)
        text = (response.text or "").strip()
        if not text:
            return "Not enough data available."
        if "Not enough data" in text:
            return "Not enough data available."
        return text
    except Exception:
        return "Not enough data available."


def calculate_health_score(dfs):
    """Calculate overall business health score (0-100)"""
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
    """Categorize all insights by priority: Critical, Important, Monitor"""
    critical = []
    important = []
    monitor = []
    opportunities = []
    
    try:
        # Analyze key metrics for categorization
        cash_res = FinancialAnalyzer.analyze_cash(dfs)
        runway = cash_res.get('runway_months', 999)
        
        ar_res = FinancialAnalyzer.analyze_ar(dfs)
        total_ar = ar_res.get('total_ar', 0)
        aging = ar_res.get('aging_table', pd.DataFrame())
        
        ov = FinancialAnalyzer.analyze_overview(dfs)
        profit_margin = ov.get('net_profit_margin', 0)
        
        # Process insights from each mode
        for mode, insight_data in all_insights.items():
            bullets = insight_data.get('bullets', []) if isinstance(insight_data, dict) else insight_data
            
            for insight in bullets:
                insight_lower = insight.lower()
                
                # Critical patterns
                if any(word in insight_lower for word in ['critical', 'urgent', 'alert', 'warning', 'low runway', 'overdue', 'loss']):
                    critical.append(f"[{mode}] {insight}")
                # Opportunity patterns
                elif any(word in insight_lower for word in ['growing', 'up ', 'momentum', 'healthy', 'improving', 'positive']):
                    opportunities.append(f"[{mode}] {insight}")
                # Important patterns
                elif any(word in insight_lower for word in ['review', 'collections', 'cash need', 'burn', 'margin']):
                    important.append(f"[{mode}] {insight}")
                # Everything else is monitoring
                else:
                    monitor.append(f"[{mode}] {insight}")
        
        # Add metric-based critical items
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
        'critical': critical[:5],  # Top 5 most critical
        'important': important[:7],
        'monitor': monitor[:8],
        'opportunities': opportunities[:5]
    }


def render_ai_insights(dfs, ai, ai_enabled=True):
    """Render the production-ready AI Insights tab.

    Follows the user's contract: OneDrive Excel is the single source of truth.
    All metrics and anomalies are computed in Python before any Gemini call.
    """
    # Pick primary DF
    if isinstance(dfs, pd.DataFrame):
        df = dfs
    elif isinstance(dfs, dict):
        df = None
        for v in dfs.values():
            if isinstance(v, pd.DataFrame) and not v.empty:
                df = v
                break
    else:
        df = None

    st.header("🤖 AI Business Intelligence")
    st.caption("Executive financial intelligence — data from connected OneDrive Excel only.")

    # Sidebar settings (anomaly thresholds)
    with st.sidebar:
        st.markdown("---")
        st.subheader("Anomaly Settings")
        spike_threshold = st.slider("Spike Threshold (%)", 50, 1000, 300, 50)
        drop_threshold = st.slider("Drop Threshold (%)", -99, -5, -30, 5)
        z_threshold = st.slider("Z-Score Threshold", 1.0, 5.0, 3.0, 0.1)

    # Block if no OneDrive data
    if df is None or getattr(df, 'empty', True):
        st.warning("AI Insights requires a connected OneDrive Excel file. Load OneDrive data to enable insights and Ask AI.")
        return

    # Cache key for session
    fp = _df_fingerprint(df)
    cached = st.session_state.get('ai_insights_cache', {})
    cached_key = st.session_state.get('ai_insights_cache_key')

    if cached and cached_key == fp:
        insights_bundle = cached
    else:
        # Compute everything deterministically in Python
        health_score = calculate_health_score(dfs)

        # Key area summaries
        sales_res = FinancialAnalyzer.analyze_sales(dfs)
        profit_res = FinancialAnalyzer.analyze_profit(dfs)
        cash_res = FinancialAnalyzer.analyze_cash(dfs)
        ar_res = FinancialAnalyzer.analyze_ar(dfs)
        ap_res = FinancialAnalyzer.analyze_ap(dfs)
        spending_res = FinancialAnalyzer.analyze_spending(dfs)

        # Build key insights (rule-based bullets)
        key_insights = []
        s = _summarize_sales(sales_res, [], [])
        if s:
            key_insights.append(s)
        p = _summarize_profitability(profit_res, [])
        if p:
            key_insights.append(p)
        c = _summarize_cash(cash_res)
        if c:
            key_insights.append(c)
        ar_txt = _summarize_ar(ar_res)
        if ar_txt:
            key_insights.append(ar_txt)
        spend_txt = _summarize_spending(spending_res, [])
        if spend_txt:
            key_insights.append(spend_txt)

        # Anomalies (strictly from df)
        anomalies_df = FinancialAnalyzer.detect_anomalies(dfs, spike_threshold, drop_threshold, z_threshold)
        anomalies_list = []
        if not anomalies_df.empty:
            for _, r in anomalies_df.iterrows():
                # Simple severity mapping
                severity = 'Low'
                try:
                    pct = float(r.get('MoM_Growth_Pct', 0))
                    if 'Drop' in str(r.get('Anomaly_Type', '')) and pct < -50:
                        severity = 'High'
                    elif pct > spike_threshold or pct < drop_threshold:
                        severity = 'Medium'
                except Exception:
                    severity = 'Low'
                anomalies_list.append({
                    'product': r.get('Product'),
                    'month': r.get('Month'),
                    'type': r.get('Anomaly_Type'),
                    'value': float(r.get('Revenue', 0)) if pd.notna(r.get('Revenue', None)) else None,
                    'severity': severity,
                    'source_columns': ['Product', 'Month', 'Revenue', 'MoM_Growth_Pct']
                })

        # Data warnings & limitations
        warnings = []
        cols_lower = [c.lower() for c in df.columns]
        if not any('cog' in c or 'cost of goods' in c for c in cols_lower):
            warnings.append('COGS not present — gross margin calculations may be incomplete')
        if not any('ar' in c or 'receivable' in c for c in cols_lower) and (not ar_res or not ar_res.get('total_ar')):
            warnings.append('Accounts Receivable (AR) data missing or incomplete')
        if not any('ap' in c or 'payable' in c for c in cols_lower) and (not ap_res or not ap_res.get('total_open')):
            warnings.append('Accounts Payable (AP) data missing or incomplete')
        if not any('inventory' in c for c in cols_lower):
            warnings.append('Inventory data not present — cannot analyze turnover or stock')
        # Period availability
        date_cols = [c for c in df.columns if 'date' in c.lower()]
        if not date_cols:
            warnings.append('No date column detected — prior-period comparisons unavailable')

        # Top drivers affecting health score (simple extraction)
        drivers = []
        try:
            if sales_res and sales_res.get('by_product') is not None and not sales_res.get('by_product').empty:
                top_rev = sales_res.get('by_product').groupby('Product')['Revenue'].sum().nlargest(3)
                drivers += [f"Revenue: {i} (${v:,.0f})" for i, v in top_rev.items()]
        except Exception:
            pass
        if cash_res and cash_res.get('runway_months') is not None:
            drivers.append(f"Runway: {cash_res.get('runway_months'):.1f} months")

        insights_bundle = {
            'health_score': health_score,
            'health_status': ('Healthy' if health_score>=80 else 'Moderate Risk' if health_score>=60 else 'High Risk'),
            'drivers': drivers[:3],
            'key_insights': key_insights,
            'anomalies': anomalies_list,
            'warnings': warnings,
            'raw_anomalies_df': anomalies_df if not anomalies_df.empty else pd.DataFrame()
        }

        # cache in session
        st.session_state['ai_insights_cache'] = insights_bundle
        st.session_state['ai_insights_cache_key'] = fp

    # === Render UI Sections in order ===
    # 1) Business Health Score
    hs = insights_bundle['health_score']
    status = insights_bundle['health_status']
    color = '#10B981' if hs>=80 else '#F59E0B' if hs>=60 else '#EF4444'

    st.markdown(f"""
    <div style="padding:12px;border-radius:10px;border:1px solid {color};background:#0b1220;margin-bottom:12px;">
      <div style="display:flex;justify-content:space-between;align-items:center;">
        <div>
          <h3 style="margin:0;color:#fff;">Business Health Score</h3>
          <div style="color:#9ca3af;font-size:12px;">Status: {status}</div>
        </div>
        <div style="text-align:right">
          <div style="font-size:36px;color:{color};font-weight:700">{hs}</div>
        </div>
      </div>
      <div style="margin-top:8px;color:#d1d5db">Top drivers: {', '.join(insights_bundle.get('drivers', []) )}</div>
    </div>
    """, unsafe_allow_html=True)

    # 2) Key Financial Insights
    st.subheader("Key Financial Insights")
    if insights_bundle['key_insights']:
        for k in insights_bundle['key_insights']:
            st.markdown(f"- {k}")
    else:
        st.info("No deterministic insights could be computed from the data.")

    # 3) Risks & Anomalies
    st.subheader("Risks & Anomalies")
    if insights_bundle['anomalies']:
        for a in insights_bundle['anomalies']:
            sev = a.get('severity', 'Low')
            tone = '⚠️' if sev=='Medium' else '🚨' if sev=='High' else 'ℹ️'
            st.markdown(f"{tone} **{a.get('product')}** — {a.get('month')}: {a.get('type')} — Severity: {sev}")
    else:
        st.success("No anomalies detected by rule-based checks.")

    # 4) Data Warnings & Limitations
    st.subheader("Data Warnings & Limitations")
    if insights_bundle['warnings']:
        for w in insights_bundle['warnings']:
            st.warning(w)
    else:
        st.info("All required fields appear present for the selected analyses.")

    # 5) Ask AI (Explanation Only)
    st.markdown("---")
    st.subheader("Ask AI (Explanation Only)")
    st.caption("AI will only explain precomputed insights. It will not compute or invent numbers.")

    user_q = st.text_input("Ask a question about these insights:", key='ai_insights_question')
    ask_btn = st.button("Explain", key='ai_insights_ask')

    if ask_btn:
        # Contract enforcement: do not call Gemini if no df
        if df is None or getattr(df, 'empty', True):
            st.warning("Cannot call AI: OneDrive Excel data is not loaded.")
        else:
            # Build strict prompt per contract
            bhs = insights_bundle['health_score']
            insights_text = '\n'.join([('- ' + i) for i in insights_bundle.get('key_insights', [])]) or 'None'
            anomalies_text = json.dumps(insights_bundle.get('anomalies', []), indent=2, default=str)
            warnings_text = '\n'.join(['- ' + w for w in insights_bundle.get('warnings', [])]) or 'None'

            prompt = (
                "You are a financial analyst.\n"
                "Use ONLY the data provided below.\n"
                "Do NOT assume, estimate, or invent numbers.\n\n"
                f"Business Health Score:\n{bhs}\n\n"
                f"Insights:\n{insights_text}\n\n"
                f"Anomalies:\n{anomalies_text}\n\n"
                f"Warnings:\n{warnings_text}\n\n"
                f"User question:\n{user_q.strip()}"
            )

            # If Gemini not configured, show message
            if genai is None:
                st.error("Gemini SDK not available in this environment. Set up google-genai and configure API key.")
            else:
                try:
                    client = genai.Client(api_key=ai.api_key if getattr(ai, 'api_key', None) else st.secrets.get('GEMINI_API_KEY'))
                    resp = client.models.generate_content(
                        model='gemini-2.0-flash',
                        contents=prompt
                    )
                    text = getattr(resp, 'text', '') or str(resp)
                    # If model tries to invent or says cannot answer, enforce contract message
                    if not text.strip():
                        st.info("This question cannot be answered from the available Excel data.")
                    else:
                        # Simple guard: if response contains 'not enough' or 'cannot', map to canonical message
                        low = text.lower()
                        if 'not enough' in low or 'cannot be answered' in low or 'insufficient' in low:
                            st.info("This question cannot be answered from the available Excel data.")
                        else:
                            st.markdown(text)
                            st.info("⚠ AI interpretation is based ONLY on the precomputed insights provided above.")
                except Exception as e:
                    msg = str(e)
                    if '429' in msg or 'RESOURCE_EXHAUSTED' in msg:
                        st.warning('AI quota exhausted — try again later.')
                    elif '404' in msg:
                        st.warning('AI model unavailable.')
                    else:
                        st.warning(f'AI call failed: {msg}')


def _render_insight_card(title, bullets, color="#6366F1"):
    """Helper to render an insight card with consistent styling"""
    st.markdown(f"""
    <div style="background-color: #1e293b; padding: 20px; border-radius: 12px; 
                border-left: 5px solid {color}; margin-bottom: 15px;">
        <h4 style="margin: 0 0 15px 0; color: #f9fafb;">{title}</h4>
    </div>
    """, unsafe_allow_html=True)
    
    if bullets and len(bullets) > 0:
        for bullet in bullets:
            st.markdown(f"• {bullet}")
    else:
        st.info("No insights available for this area")
