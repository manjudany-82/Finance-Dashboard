"""
AI Business Insights Tab - Consolidated Executive Intelligence
Provides comprehensive AI-powered analysis across all financial areas
"""

import streamlit as st
import pandas as pd
from financial_analyzer.analysis_modes import FinancialAnalyzer
from financial_analyzer.render_layouts import _get_batched_insights


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
    """Render the comprehensive AI Business Insights tab"""
    
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
    
    # Get all insights
    all_insights = _get_batched_insights(ai, dfs, ai_enabled)
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
