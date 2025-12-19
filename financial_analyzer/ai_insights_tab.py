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
from financial_analyzer.insights_core import categorize_insights, compute_financial_insights
from financial_analyzer import metrics as metrics_module
from financial_analyzer.metrics import calculate_health_score_v2
from financial_analyzer import llm_insights

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


# `calculate_health_score` is implemented in `financial_analyzer.insights_core`
# and imported at module top to keep this UI module focused on rendering.


# `categorize_insights` is implemented in `financial_analyzer.insights_core`
# and imported at module top to keep this UI module focused on rendering.


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
        st.info("Connect financial data to see your Business Health Score.")
        return

    # Cache key for session
    fp = _df_fingerprint(df)
    cached = st.session_state.get('ai_insights_cache', {})
    cached_key = st.session_state.get('ai_insights_cache_key')

    if cached and cached_key == fp:
        insights_bundle = cached
    else:
        # Compute everything deterministically in Python
        fin_insights = compute_financial_insights(df)
        # V2: deterministic explainable health score computed from the OneDrive-loaded DataFrame
        v2_result = calculate_health_score_v2(df)
        # Keep legacy health_info for compatibility but prefer v2_result for UI rendering
        health_info = metrics_module.calculate_health_score(fin_insights)
        health_score = int(v2_result.get('score', health_info.get('health_score', 0)))

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
            # surface V2 values as primary deterministic health indicators
            'health_score': health_score,
            'health_band': v2_result.get('band') or (health_info.get('health_band') if isinstance(health_info, dict) else None),
            'health_v2_components': v2_result.get('components', {}),
            'health_v2_positives': v2_result.get('positives', []),
            'health_v2_risks': v2_result.get('risks', []),
            'top_positive_factors': health_info.get('top_positive_factors') if isinstance(health_info, dict) else [],
            'top_risks': health_info.get('top_risks') if isinstance(health_info, dict) else [],
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
        # 1) Business Health Score (V2) - deterministic UI-only card with component breakdown
        v2_score = insights_bundle.get('health_score', 0)
        v2_band = insights_bundle.get('health_band', '')
        components = insights_bundle.get('health_v2_components', {})
        positives = insights_bundle.get('health_v2_positives') or insights_bundle.get('top_positive_factors') or insights_bundle.get('drivers') or []
        risks = insights_bundle.get('health_v2_risks') or insights_bundle.get('top_risks') or []

        # Band color mapping per spec
        band_colors = {
            'Excellent': '#10B981',
            'Healthy': '#3B82F6',
            'Watch': '#F59E0B',
            'At Risk': '#EF4444'
        }
        band_color = band_colors.get(v2_band, '#6B7280')

        with st.container():
            st.markdown(f"""
            <div style='display:flex;align-items:center;justify-content:space-between;margin-bottom:12px'>
              <div style='flex:1'>
                <h3 style='margin:0'>Business Health Score (V2)</h3>
                <div style='font-size:38px;font-weight:800'>{int(v2_score)}/100</div>
                <div style='margin-top:6px'>
                  <span style='padding:6px 10px;border-radius:10px;background-color:{band_color};color:#ffffff;font-weight:700'>{v2_band}</span>
                </div>
              </div>
              <div style='width:48%;padding-left:16px'>
                <div style='font-size:14px;color:#6b7280'>Deterministic component breakdown</div>
                <div style='margin-top:8px'>
            """, unsafe_allow_html=True)

            # Render components compactly with bars and notes
            for key_label, comp in [('Revenue Trend', components.get('revenue_trend', {})),
                                     ('Profitability', components.get('profitability', {})),
                                     ('Cash Stability', components.get('cash_stability', {})),
                                     ('Volatility', components.get('volatility', {}))]:
                score_val = int(comp.get('score', 0) or 0)
                note = comp.get('note', '') or ''
                # tooltip titles per requirement
                tooltip_map = {
                    'Revenue Trend': 'Revenue Trend → growth/decline consistency',
                    'Profitability': 'Profitability → margin strength & stability',
                    'Cash Stability': 'Cash Stability → cash flow reliability',
                    'Volatility': 'Volatility → penalty for large swings'
                }
                tooltip = tooltip_map.get(key_label, '')
                # row
                col1, col2 = st.columns([2, 1], gap='small')
                with col1:
                    st.markdown(f"**{key_label}** <span title='{tooltip}'>ℹ️</span>")
                    st.progress(min(1.0, max(0.0, score_val / 100.0)))
                with col2:
                    st.markdown(f"**{score_val}**")
                    if note:
                        st.caption(note)

            # Positives and Risks (two compact columns)
            colp, colr = st.columns(2, gap='large')
            with colp:
                st.markdown("**What's working well**")
                if positives:
                    for p in positives[:5]:
                        st.markdown(f"- {p}")
                else:
                    st.markdown("- No strong positives detected")
            with colr:
                st.markdown("**Risks to watch**")
                if risks:
                    for r in risks[:5]:
                        st.markdown(f"- {r}")
                else:
                    st.markdown("- No immediate risks detected")

            st.markdown("</div></div>", unsafe_allow_html=True)
        # === Executive Summary (AI) section (below V2 card) ===
        # Data contract: only use calculate_health_score_v2 outputs, compute_financial_insights, and anomalies from the OneDrive DF
        # Cache key for exec summary per data fingerprint
        exec_cache = st.session_state.get('exec_summary_cache', {})
        exec_cached_key = exec_cache.get('key')
        if exec_cached_key == fp and exec_cache.get('value'):
            exec_text = exec_cache['value']
        else:
            # Build structured input strictly from deterministic sources
            structured = {
                'score': int(insights_bundle.get('health_score', 0)),
                'band': insights_bundle.get('health_band'),
                'revenue_trend': components.get('revenue_trend', {}),
                'profitability': components.get('profitability', {}),
                'cash_stability': components.get('cash_stability', {}),
                'volatility': components.get('volatility', {}),
                'positives': list(positives)[:5],
                'risks': list(risks)[:5],
                'anomalies': insights_bundle.get('anomalies', [])
            }

            # Rule-based deterministic summary (fallback and baseline)
            try:
                s = structured['score']
                band = structured.get('band') or ''
                overall = f"Overall: Business Health Score {s}/100 — {band}."

                if structured['positives']:
                    positives_txt = '; '.join(structured['positives'][:2])
                    working = f"What's working: {positives_txt}."
                else:
                    working = "What's working: No strong positives detected from recent financials."

                if structured['risks']:
                    risks_txt = '; '.join(structured['risks'][:2])
                    risks_sentence = f"Risks: {risks_txt}."
                elif structured['anomalies']:
                    risks_sentence = "Risks: Recent anomalies detected in revenue or other accounts."
                else:
                    risks_sentence = "Risks: No immediate risks detected."

                rule_summary = ' '.join([overall, working, risks_sentence])
            except Exception:
                rule_summary = "Executive summary unavailable due to data formatting."

            # Prefer LLM rephrase only if GEMINI key present and structured non-empty
            exec_text = rule_summary
            try:
                import os
                if os.getenv('GEMINI_API_KEY'):
                    non_empty = any([structured.get('score') is not None, structured.get('anomalies'), structured.get('positives'), structured.get('risks')])
                    if non_empty:
                        user_q = "Write a concise 3-sentence executive summary of the business health using ONLY the provided structured insights. Keep deterministic phrasing first."
                        llm_resp = llm_insights.generate_llm_response(structured, user_q)
                        if llm_resp.get('ok') and llm_resp.get('text'):
                            exec_text = llm_resp.get('text').strip()
            except Exception:
                exec_text = rule_summary

            # Cache per data fingerprint
            st.session_state['exec_summary_cache'] = {'key': fp, 'value': exec_text}

        # Render Executive Summary container
        with st.container():
            st.markdown("<div style='background-color:#fbfbff;border:1px solid #e6e6f0;padding:12px;border-radius:8px'>", unsafe_allow_html=True)
            st.markdown("### 🧠 Executive Summary (AI)")
            st.caption("Plain-English interpretation of your financial performance")
            st.write(exec_text)
            st.markdown("*Generated from your OneDrive financials*")
            st.markdown("</div>", unsafe_allow_html=True)

        # === ⚠️ Top Risks & Early Warnings ===
        # Must derive risks only from deterministic sources (v2, compute_financial_insights, anomalies)
        # Recompute deterministic inputs (do not rely on cached UI state)
        try:
            fresh_fin_insights = compute_financial_insights(df)
        except Exception:
            fresh_fin_insights = {}

        try:
            fresh_v2 = calculate_health_score_v2(df)
        except Exception:
            fresh_v2 = {'components': {}, 'risks': [], 'score': 0, 'band': None}

        try:
            fresh_anoms_df = FinancialAnalyzer.detect_anomalies(dfs, spike_threshold, drop_threshold, z_threshold)
        except Exception:
            fresh_anoms_df = pd.DataFrame()

        normalized = []

        # Helper to add normalized risk (avoid duplicates by title)
        def _add_risk(risk):
            if not any(r['title'] == risk['title'] for r in normalized):
                normalized.append(risk)

        comps = fresh_v2.get('components', {})

        # Revenue decline
        rev = comps.get('revenue_trend', {})
        rev_score = int(rev.get('score', 0) or 0)
        rev_note = rev.get('note', '') or ''
        if rev_score <= 30 or 'declin' in rev_note.lower() or 'drop' in rev_note.lower():
            _add_risk({
                'id': 'revenue_decline',
                'title': 'Declining revenue trend',
                'severity': 'High',
                'explanation': rev_note or 'Recent revenue trend indicates decline',
                'metric_source': 'revenue_trend'
            })

        # Volatility
        vol = comps.get('volatility', {})
        vol_score = int(vol.get('score', 0) or 0)
        vol_note = vol.get('note', '') or ''
        if vol_score <= 30 or 'volatil' in vol_note.lower() or 'swing' in vol_note.lower():
            sev = 'High' if vol_score <= 20 else 'Medium'
            _add_risk({
                'id': 'revenue_volatility',
                'title': 'High revenue volatility',
                'severity': sev,
                'explanation': vol_note or 'Revenue shows large month-to-month swings',
                'metric_source': 'volatility'
            })

        # Profitability / margin compression
        prof = comps.get('profitability', {})
        prof_score = int(prof.get('score', 0) or 0)
        prof_note = prof.get('note', '') or ''
        if prof_score <= 40 or 'loss' in prof_note.lower() or 'net loss' in prof_note.lower():
            sev = 'High' if 'loss' in prof_note.lower() or prof_score <= 20 else 'Medium'
            _add_risk({
                'id': 'margin_compression',
                'title': 'Margin compression / low profitability',
                'severity': sev,
                'explanation': prof_note or 'Profitability is weak or declining',
                'metric_source': 'profitability'
            })

        # Cash stability
        cash = comps.get('cash_stability', {})
        cash_score = int(cash.get('score', 0) or 0)
        cash_note = cash.get('note', '') or ''
        if cash_score <= 40 or 'negative' in cash_note.lower():
            sev = 'High' if 'negative' in cash_note.lower() or cash_score <= 20 else 'Medium'
            _add_risk({
                'id': 'cash_instability',
                'title': 'Unstable cash position',
                'severity': sev,
                'explanation': cash_note or 'Cash balance or stability is a concern',
                'metric_source': 'cash_stability'
            })

        # Add v2 explicit risks strings as Low unless detected above
        for rstr in (fresh_v2.get('risks') or [])[:5]:
            title = rstr if len(rstr) < 60 else rstr[:57] + '...'
            _add_risk({
                'id': f'v2_text_{hash(rstr)}',
                'title': title,
                'severity': 'Low',
                'explanation': rstr,
                'metric_source': 'v2_risks'
            })

        # Add anomalies from data (each anomaly is Low/Medium/High depending on magnitude)
        if not fresh_anoms_df.empty:
            for _, ar in fresh_anoms_df.iterrows():
                try:
                    pct = float(ar.get('MoM_Growth_Pct', 0))
                except Exception:
                    pct = 0
                sev = 'Low'
                if abs(pct) >= 50:
                    sev = 'High'
                elif abs(pct) >= 20:
                    sev = 'Medium'
                title = f"Anomaly: {ar.get('Product')} {ar.get('Month')}"
                expl = f"{ar.get('Anomaly_Type')} {pct:+.1f}% (${float(ar.get('Revenue',0)) if pd.notna(ar.get('Revenue',None)) else 0:,.0f})"
                _add_risk({
                    'id': f'anom_{hash((ar.get("Product"), ar.get("Month")))}',
                    'title': title,
                    'severity': sev,
                    'explanation': expl,
                    'metric_source': 'anomaly'
                })

        # Sort by severity (High > Medium > Low) and cap to top 5
        severity_rank = {'High': 3, 'Medium': 2, 'Low': 1}
        normalized.sort(key=lambda x: (-severity_rank.get(x.get('severity', 'Low'), 1), x.get('title')))
        normalized = normalized[:5]

        # Optional LLM rephrase for explanations (must not change severity or add risks)
        rephrased = []
        try:
            import os
            allow_llm = bool(os.getenv('GEMINI_API_KEY'))
        except Exception:
            allow_llm = False

        for r in normalized:
            explanation = r['explanation']
            if allow_llm and explanation:
                try:
                    q = "Rephrase this one-line factual explanation for clarity, without changing severity or adding new information: '" + explanation + "'"
                    resp = llm_insights.generate_llm_response({'title': r['title'], 'severity': r['severity'], 'explanation': explanation}, q)
                    if resp.get('ok') and resp.get('text'):
                        # Use the LLM text but keep severity unchanged
                        r['explanation'] = resp.get('text').strip()
                except Exception:
                    pass
            rephrased.append(r)

        # Render risk card
        if not rephrased:
            st.success("No critical financial risks detected based on current data.")
        else:
            with st.container():
                st.markdown("### ⚠️ Top Risks & Early Warnings")
                st.markdown("<div style='background-color:#fff7f5;border:1px solid #ffe6e0;padding:10px;border-radius:8px'>", unsafe_allow_html=True)
                for r in rephrased:
                    color = '#ef4444' if r['severity'] == 'High' else '#f59e0b' if r['severity'] == 'Medium' else '#6b7280'
                    st.markdown(f"<div style='display:flex;justify-content:space-between;align-items:center;padding:6px 0;border-bottom:1px solid #f3f4f6'>", unsafe_allow_html=True)
                    st.markdown(f"<div style='flex:1'><strong>{r['title']}</strong><div style='color:#374151;font-size:13px'>{r['explanation']}</div></div><div style='margin-left:12px'><span style='background:{color};color:#fff;padding:6px 8px;border-radius:8px;font-weight:700'>{r['severity']}</span></div>", unsafe_allow_html=True)
                    st.markdown("</div>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
                st.caption("Based on analysis of your OneDrive financial data")
        # End risks
        st.divider()

        # === 🎯 Focus Areas & Next Actions (30–60 days) ===
        # Placement: immediately below risks. Deterministic mapping from v2 and normalized risks only.
        # Guardrail: require df present
        if df is None or getattr(df, 'empty', True):
            st.info("Connect financial data to see priority actions.")
            return

        # Build actions from deterministic signals
        actions = []

        # Helper to append unique action by title
        def _add_action(title, explanation, category):
            if not any(a['title'] == title for a in actions):
                actions.append({'title': title, 'explanation': explanation, 'category': category})

        # Use fresh_v2 components and rephrased risks from above if available
        v2_comps = fresh_v2.get('components', {}) if 'fresh_v2' in locals() else {}

        # Rule mappings
        # Declining revenue -> Stabilize revenue sources
        rev_comp = v2_comps.get('revenue_trend', {})
        rev_score = int(rev_comp.get('score', 0) or 0)
        if any(r.get('id') == 'revenue_decline' for r in normalized) or rev_score <= 40:
            _add_action(
                'Stabilize revenue sources',
                'Prioritize securing consistent revenue: focus on highest-performing products, re-evaluate pricing where downward trends are evident, and monitor month-over-month sales.',
                'Revenue'
            )

        # High volatility -> Tighten forecasting & monthly tracking
        vol_comp = v2_comps.get('volatility', {})
        vol_score = int(vol_comp.get('score', 0) or 0)
        if any(r.get('id') == 'revenue_volatility' for r in normalized) or vol_score <= 50:
            _add_action(
                'Tighten forecasting & monthly tracking',
                'Increase cadence of revenue and cash forecasts, track key drivers monthly, and flag large month-to-month swings for review.',
                'Risk Monitoring'
            )

        # Margin compression -> Review pricing and cost structure
        prof_comp = v2_comps.get('profitability', {})
        prof_score = int(prof_comp.get('score', 0) or 0)
        if any(r.get('id') == 'margin_compression' for r in normalized) or prof_score <= 50:
            _add_action(
                'Review pricing and cost structure',
                'Assess product-level margins and controllable expenses; consider targeted price adjustments or cost reductions where margins have compressed.',
                'Costs'
            )

        # Cash instability -> Preserve liquidity
        cash_comp = v2_comps.get('cash_stability', {})
        cash_score = int(cash_comp.get('score', 0) or 0)
        if any(r.get('id') == 'cash_instability' for r in normalized) or cash_score <= 45:
            _add_action(
                'Preserve liquidity & defer non-essential spend',
                'Prioritize actions that conserve cash and extend runway, postponing discretionary investments until stability improves.',
                'Cash'
            )

        # If no actions detected, provide monitoring action
        if not actions:
            _add_action(
                'Maintain monitoring cadence',
                'No major signals detected; continue regular monitoring of revenue, margins, and cash, and revisit if trends change.',
                'Risk Monitoring'
            )

        # Cap at 4 items
        actions = actions[:4]

        # Optional LLM rephrase for clarity only
        try:
            import os
            allow_llm = bool(os.getenv('GEMINI_API_KEY'))
        except Exception:
            allow_llm = False

        rephrased_actions = []
        for act in actions:
            expl = act['explanation']
            if allow_llm and expl:
                try:
                    q = "Rephrase this 1-2 sentence action for clarity without adding new recommendations or numeric targets: '" + expl + "'"
                    resp = llm_insights.generate_llm_response({'title': act['title'], 'explanation': expl, 'category': act['category']}, q)
                    if resp.get('ok') and resp.get('text'):
                        expl = resp.get('text').strip()
                except Exception:
                    pass
            rephrased_actions.append({'title': act['title'], 'explanation': expl, 'category': act['category']})

        # Render the numbered action list
        with st.container():
            st.markdown('### 🎯 Focus Areas & Next Actions (30–60 days)')
            st.markdown("<div style='padding:6px 0 0 0'>", unsafe_allow_html=True)
            for i, a in enumerate(rephrased_actions, start=1):
                st.markdown(f"**{i}. {a['title']}** — {a['explanation']}  ")
                st.caption(f"Category: {a['category']}")
            st.markdown("</div>", unsafe_allow_html=True)
            st.caption('Suggested priorities based on current financial signals')
        st.divider()

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

            # Use centralized LLM helper which enforces guardrails
            result = llm_insights.generate_llm_response(
                {
                    'business_health_score': insights_bundle.get('health_score'),
                    'insights': insights_bundle.get('key_insights'),
                    'anomalies': insights_bundle.get('anomalies'),
                    'warnings': insights_bundle.get('warnings')
                },
                user_q or ''
            )

            if not result.get('ok'):
                st.info(result.get('text') or 'This question cannot be answered from the available Excel data.')
            else:
                st.markdown(result.get('text'))
                st.info('⚠ AI interpretation is based ONLY on the precomputed insights provided above.')


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


def render_health_card(score: int, band: str, positives: list, risks: list):
    """UI-only helper: render deterministic Business Health Score card.

    - `score`: int 0-100
    - `band`: one of 'Strong', 'Stable', 'Risk'
    - `positives`: list of short strings
    - `risks`: list of short strings
    This helper must not compute or fetch data — it only renders.
    """
    # Color mapping for visual band indicator
    band_colors = {
        'Strong': '#10B981',
        'Stable': '#F59E0B',
        'Risk': '#EF4444'
    }
    color = band_colors.get(band, '#6B7280')

    tooltip = (
        "Deterministic score (0–100) summarizing profitability, revenue stability, "
        "expense discipline, liquidity, and data quality. Computed from accounting data only; "
        "this score is rule-based and not produced by AI."
    )

    with st.container():
        left, right = st.columns([1, 2], gap='small')
        with left:
            # Large numeric display
            st.metric(label="Business Health Score", value=f"{int(score)}/100", delta=None, help=tooltip)
            st.caption("Rule-based, deterministic — not generated by AI")
        with right:
            st.markdown(f"**Status:** <span style='color:{color};font-weight:700'>{band}</span>", unsafe_allow_html=True)
            st.markdown("**What's going well**")
            if positives:
                for p in positives[:5]:
                    st.markdown(f"- {p}")
            else:
                st.markdown("- No strong positives detected")

            st.markdown("**Key risks**")
            if risks:
                for r in risks[:5]:
                    st.markdown(f"- {r}")
            else:
                st.markdown("- No immediate risks detected")
