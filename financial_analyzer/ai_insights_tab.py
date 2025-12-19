"""
AI Business Insights Tab - Consolidated Executive Intelligence
Provides comprehensive AI-powered analysis across all financial areas
"""

import streamlit as st
import pandas as pd
from financial_analyzer.analysis_modes import FinancialAnalyzer
from financial_analyzer.render_layouts import _get_batched_insights

try:
    import google.generativeai as genai
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
    """
    Render the comprehensive AI Business Insights tab.
    
    CANONICAL ENTRY POINT for "🤖 AI Insights" tab rendering.
    Called from dashboard.py tabs[1] with (dfs, ai, ai_enabled).
    """
    
    # DEBUG: Verify render_ai_insights is actually being called
    st.error("🚨 DEBUG: render_ai_insights() CALLED 🚨")
    
    st.header("🤖 AI Business Intelligence")
    st.caption("Consolidated executive insights powered by AI analysis across all financial areas")
    
    # User controls in sidebar
    with st.sidebar:
        st.markdown("---")
        st.subheader("🎯 Anomaly Detection Settings")
        spike_threshold = st.slider("Spike Threshold (%)", 100, 500, 300, 50, 
                                    help="Growth % above this is flagged as spike")
        drop_threshold = st.slider("Drop Threshold (%)", -90, -10, -50, 10,
                                   help="Growth % below this is flagged as drop")
        z_threshold = st.slider("Z-Score Threshold", 2.0, 4.0, 3.0, 0.5,
                               help="Statistical significance level")

    # Determine source label without triggering LLM calls yet (keeps UI non-blocking)
    source = 'AI' if ai_enabled and ai.api_key and not getattr(ai, 'quota_exhausted', False) else 'Rule-Based'
    
    # Calculate health score
    health_score = calculate_health_score(dfs)
    
    # Health score display with color coding
    if health_score >= 80:
        health_color = "#10B981"  # Green
        health_status = "Excellent"
        health_icon = "✅"
    elif health_score >= 60:
        health_color = "#F59E0B"  # Orange
        health_status = "Good"
        health_icon = "⚠️"
    else:
        health_color = "#EF4444"  # Red
        health_status = "Needs Attention"
        health_icon = "🚨"
    
    # Compact Executive Summary Box
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); 
                padding: 16px 24px; border-radius: 12px; border: 2px solid {health_color}; 
                box-shadow: 0 8px 32px rgba(0,0,0,0.4); margin-bottom: 20px;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <h2 style="margin: 0; color: #f9fafb; font-size: 1.25rem;">
                    {health_icon} Business Health Score
                </h2>
                <p style="color: #9ca3af; margin: 5px 0 0 0; font-size: 0.75rem;">
                    Analysis Source: {source}
                </p>
            </div>
            <div style="text-align: right;">
                <div style="font-size: 2.5rem; font-weight: 700; color: {health_color}; line-height: 1;">
                    {health_score}
                </div>
                <div style="font-size: 0.9rem; color: {health_color}; font-weight: 600;">
                    {health_status}
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # DEPRECATED: This function is no longer called by dashboard.py
    # The Ask Your Financials (AI) section is now rendered directly in dashboard.py tabs[1]
    # This entire function can be removed after verification that the minimal test works.

    # Always render Ask Your Financials (AI) UI immediately (no guards)
    # NOTE: THIS FUNCTION IS NOT EXECUTED - SEE dashboard.py tabs[1] for the active code
    # st.markdown("---")
    # st.error("🚨 DEBUG: About to render Ask-Your-Financials section 🚨")
    # st.markdown("## 💬 Ask Your Financials (AI)")
    # st.caption("Ask questions about revenue, expenses, anomalies, or trends.")

    # question = st.text_input(
    #     "Example: Why did SaaS revenue drop in October?",
    #     key="ask_ai_input"
    # )

    # if not question:
    #     st.info("Enter a question above to analyze your financial data using AI.")
    # else:
    #     st.success("DEBUG: Question received — AI logic will run here.")
    #     # TODO: Re-attach structured retrieval + Gemini call here.

    # Defer LLM-backed batch insights and add a short timeout so health checks don't hang
    # If the call exceeds the timeout, we fall back to rule-based insights immediately.
    all_insights = None
    try:
        from concurrent.futures import ThreadPoolExecutor

        def _safe_fetch():
            return _get_batched_insights(ai, dfs, ai_enabled)

        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(_safe_fetch)
            all_insights = future.result(timeout=8)
    except Exception:
        # On timeout or any error, fall back to rule-based insights to keep UI responsive
        all_insights = _get_batched_insights(ai, dfs, ai_enabled=False)
    
    # ===== ANOMALY ALERTS SECTION =====
    st.markdown("---")
    st.subheader("⚠️ Anomaly Alerts - Product Revenue")
    
    # Detect anomalies
    anomalies_df = FinancialAnalyzer.detect_anomalies(dfs, spike_threshold, drop_threshold, z_threshold)
    
    if not anomalies_df.empty:
        # Summary metrics
        col_a, col_b, col_c = st.columns(3)
        
        total_anomalies = len(anomalies_df)
        spikes = len(anomalies_df[anomalies_df['Anomaly_Type'].str.contains('Spike', na=False)])
        drops = len(anomalies_df[anomalies_df['Anomaly_Type'].str.contains('Drop', na=False)])
        
        with col_a:
            st.metric("Total Anomalies", total_anomalies, delta=None)
        with col_b:
            st.metric("🔥 Spikes", spikes, delta=None)
        with col_c:
            st.metric("📉 Drops", drops, delta=None)
        
        # Critical alerts - show drops and major spikes
        critical_anomalies = anomalies_df[
            (anomalies_df['Anomaly_Type'].str.contains('Drop', na=False)) | 
            (anomalies_df['MoM_Growth_Pct'] > spike_threshold * 1.5)
        ]
        
        if not critical_anomalies.empty:
            st.markdown("""
            <div style="background-color: #450a0a; padding: 12px; border-radius: 8px; 
                        border: 2px solid #DC2626; margin: 16px 0;">
                <h4 style="margin: 0; color: #fca5a5; font-size: 1rem;">🚨 Critical Anomalies</h4>
            </div>
            """, unsafe_allow_html=True)
            
            for _, row in critical_anomalies.head(5).iterrows():
                if 'Drop' in row['Anomaly_Type']:
                    st.error(f"**{row['Product']}** - {row['Month']}: Revenue dropped **{row['MoM_Growth_Pct']:.1f}%** (${row['Revenue']:,.0f})")
                else:
                    st.warning(f"**{row['Product']}** - {row['Month']}: Revenue spiked **+{row['MoM_Growth_Pct']:.1f}%** (${row['Revenue']:,.0f})")
        
        # Full anomalies table
        with st.expander("📊 View All Anomalies (Sortable Table)", expanded=False):
            # Format the dataframe for display
            display_df = anomalies_df.copy()
            display_df['Revenue'] = display_df['Revenue'].apply(lambda x: f"${x:,.0f}")
            display_df['MoM_Growth_Pct'] = display_df['MoM_Growth_Pct'].apply(lambda x: f"{x:+.1f}%")
            display_df['Z_Score'] = display_df['Z_Score'].apply(lambda x: f"{x:.2f}")
            
            st.dataframe(
                display_df,
                use_container_width=True,
                height=400,
                column_config={
                    "Month": st.column_config.TextColumn("Month", width="medium"),
                    "Product": st.column_config.TextColumn("Product", width="large"),
                    "Revenue": st.column_config.TextColumn("Revenue", width="medium"),
                    "MoM_Growth_Pct": st.column_config.TextColumn("MoM Growth %", width="medium"),
                    "Anomaly_Type": st.column_config.TextColumn("Type", width="medium"),
                    "Z_Score": st.column_config.TextColumn("Z-Score", width="small")
                }
            )
            
            # Download button
            csv = anomalies_df.to_csv(index=False)
            st.download_button(
                label="📥 Download Anomalies as CSV",
                data=csv,
                file_name="product_anomalies.csv",
                mime="text/csv"
            )
    else:
        st.info("✅ No significant anomalies detected in product revenue trends.")
    
    st.markdown("---")
    
    # Categorize insights
    categorized = categorize_insights(all_insights, dfs)
    
    # Create two columns for opportunities and risks
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        <div style="background-color: #065f46; padding: 12px; border-radius: 10px; margin-bottom: 16px; border-left: 4px solid #10B981;">
            <h3 style="margin: 0; color: #d1fae5; font-size: 1rem;">📈 Top Opportunities</h3>
        </div>
        """, unsafe_allow_html=True)
        
        if categorized['opportunities']:
            for opp in categorized['opportunities']:
                st.markdown(f"• {opp}")
        else:
            st.info("No significant opportunities identified")
    
    with col2:
        st.markdown("""
        <div style="background-color: #7f1d1d; padding: 12px; border-radius: 10px; margin-bottom: 16px; border-left: 4px solid #EF4444;">
            <h3 style="margin: 0; color: #fecaca; font-size: 1rem;">🚨 Top Risks</h3>
        </div>
        """, unsafe_allow_html=True)
        
        if categorized['critical']:
            for risk in categorized['critical']:
                st.markdown(f"• {risk}")
        else:
            st.success("No critical risks identified")
    
    st.markdown("---")
    
    # Critical Actions Section
    if categorized['critical']:
        st.markdown("""
        <div style="background-color: #450a0a; padding: 16px; border-radius: 10px; 
                    border: 2px solid #DC2626; margin-bottom: 16px;">
            <h3 style="margin: 0 0 12px 0; color: #fca5a5; font-size: 1.1rem;">
                🚨 CRITICAL ACTIONS REQUIRED
            </h3>
        </div>
        """, unsafe_allow_html=True)
        
        for idx, action in enumerate(categorized['critical'], 1):
            st.markdown(f"""
            <div style="background-color: #1e293b; padding: 10px; border-radius: 8px; 
                        margin-bottom: 8px; border-left: 4px solid #DC2626;">
                <strong style="color: #fca5a5;">{idx}.</strong> 
                <span style="color: #f9fafb;">{action}</span>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Strategic Insights by Category
    st.subheader("💡 Strategic Insights by Area")
    
    # Create tabs for each business area
    area_tabs = st.tabs(["💰 Revenue", "💸 Expenses", "📥 Collections", "💵 Cash Flow", "📊 Profitability"])
    
    with area_tabs[0]:  # Revenue
        sales_insights = all_insights.get("Sales Trends", {})
        bullets = sales_insights.get('bullets', []) if isinstance(sales_insights, dict) else sales_insights
        _render_insight_card("Sales Performance", bullets, "#00CC96")
    
    with area_tabs[1]:  # Expenses
        spending_insights = all_insights.get("Spending", {})
        bullets = spending_insights.get('bullets', []) if isinstance(spending_insights, dict) else spending_insights
        _render_insight_card("Spending Analysis", bullets, "#AB63FA")
    
    with area_tabs[2]:  # Collections
        ar_insights = all_insights.get("AR Collections", {})
        bullets = ar_insights.get('bullets', []) if isinstance(ar_insights, dict) else ar_insights
        _render_insight_card("Accounts Receivable", bullets, "#FFA15A")
    
    with area_tabs[3]:  # Cash Flow
        cash_insights = all_insights.get("Cash Flow Statement", {})
        bullets = cash_insights.get('bullets', []) if isinstance(cash_insights, dict) else cash_insights
        _render_insight_card("Cash Flow Statement", bullets, "#19D3F3")
    
    with area_tabs[4]:  # Profitability
        profit_insights = all_insights.get("Profitability", {})
        bullets = profit_insights.get('bullets', []) if isinstance(profit_insights, dict) else profit_insights
        _render_insight_card("Profit & Margins", bullets, "#B6E880")
    
    st.markdown("---")
    
    # Important Items
    if categorized['important']:
        with st.expander("📋 Important Items to Review", expanded=False):
            for item in categorized['important']:
                st.markdown(f"• {item}")
    
    # Monitoring Items
    if categorized['monitor']:
        with st.expander("👀 Monitoring & Tracking", expanded=False):
            for item in categorized['monitor']:
                st.markdown(f"• {item}")


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
