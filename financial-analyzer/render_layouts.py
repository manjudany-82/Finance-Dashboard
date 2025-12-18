
import streamlit as st
import pandas as pd
import plotly.express as px
from analysis_modes import FinancialAnalyzer
from forecast_engine import ForecastEngine

# Toggle AI insights display
ENABLE_AI_INSIGHTS = False

# Global cache for batched AI insights keyed by dataset timestamp and enable flag
_global_insight_cache = {
    'ts': None,       # data_loaded_at timestamp
    'enabled': None,  # ai_enabled flag
    'data': None      # cached insights dict
}


def _get_batched_insights(ai, dfs, ai_enabled=True):
    """Collect data for all sections and retrieve batched insights.

    Caches results per data load timestamp stored in `st.session_state['data_loaded_at']`
    and per `ai_enabled` flag so insights are invalidated when the user loads new data
    or toggles AI on/off.
    """
    # If AI disabled, return rule-based fallback for each section
    if not ai_enabled:
        insight_requests = {
            "Overview": FinancialAnalyzer.analyze_overview(dfs),
            "Sales Trends": FinancialAnalyzer.analyze_sales(dfs),
            "AR Collections": FinancialAnalyzer.analyze_ar(dfs),
            "AP Management": FinancialAnalyzer.analyze_ap(dfs),
            "Cash Flow Statement": FinancialAnalyzer.analyze_cash_flow_statement(dfs),
            "Profitability": FinancialAnalyzer.analyze_profit(dfs),
            "Forecast": FinancialAnalyzer.analyze_forecast(dfs),
            "Spending": FinancialAnalyzer.analyze_spending(dfs)
        }
        return {mode: {"bullets": ai.generate_fallback_insights(mode, data), "raw": None} for mode, data in insight_requests.items()}

    # Determine current dataset timestamp and fingerprint for intelligent caching
    import streamlit as st
    ts = st.session_state.get('data_loaded_at') if 'data_loaded_at' in st.session_state else None
    
    # Create data fingerprint for better cache invalidation
    data_fingerprint = None
    try:
        if dfs and 'Sales_Monthly' in dfs:
            data_fingerprint = len(dfs.get('Sales_Monthly', pd.DataFrame()))
    except Exception:
        pass

    # If cache matches current data timestamp and enabled flag, return cached
    if _global_insight_cache['ts'] == ts and _global_insight_cache['enabled'] == ai_enabled and _global_insight_cache['data'] is not None:
        return _global_insight_cache['data']

    # Build requests and call batch LLM
    insight_requests = {
        "Overview": FinancialAnalyzer.analyze_overview(dfs),
        "Sales Trends": FinancialAnalyzer.analyze_sales(dfs),
        "AR Collections": FinancialAnalyzer.analyze_ar(dfs),
        "AP Management": FinancialAnalyzer.analyze_ap(dfs),
        "Cash Flow Statement": FinancialAnalyzer.analyze_cash_flow_statement(dfs),
        "Profitability": FinancialAnalyzer.analyze_profit(dfs),
        "Forecast": FinancialAnalyzer.analyze_forecast(dfs),
        "Spending": FinancialAnalyzer.analyze_spending(dfs)
    }

    try:
        res = ai.get_all_insights(insight_requests)
    except Exception:
        # If LLM call fails, fallback per section
        res = {mode: {"bullets": ai.generate_fallback_insights(mode, data), "raw": None} for mode, data in insight_requests.items()}

    # Update cache
    # Decide whether results are from AI or fallback
    source = 'AI'
    try:
        if not getattr(ai, 'api_key', None):
            source = 'Rule'
        elif getattr(ai, 'quota_exhausted', False):
            source = 'Rule'
    except Exception:
        source = 'Rule'

    _global_insight_cache['ts'] = ts
    _global_insight_cache['enabled'] = ai_enabled
    _global_insight_cache['data'] = res
    _global_insight_cache['source'] = source
    return res

def render_overview(dfs, ai, ai_enabled=True):
    st.header("📊 Executive Overview")
    st.caption("Key financial metrics at a glance")
    
    # Validate data availability
    if not dfs or not isinstance(dfs, dict) or len(dfs) == 0:
        st.warning("⚠️ No financial data available. Please load data from the sidebar.")
        return
    
    # --- FINANCIAL PERFORMANCE METRICS ---
    st.subheader("💰 Financial Performance (YTD)")
    c1, c2, c3 = st.columns(3)
    ov = FinancialAnalyzer.analyze_overview(dfs)
    
    c1.metric("YTD Sales", f"${ov.get('ytd_sales', 0):,.0f}")
    c2.metric("YTD Expenses", f"${ov.get('ytd_expense', 0):,.0f}", delta_color="inverse")
    
    np = ov.get('net_profit', 0)
    c3.metric("Net Profit", f"${np:,.0f}", f"{ov.get('net_profit_margin', 0):.1f}% Margin")
    
    # --- WORKING CAPITAL METRICS ---
    st.subheader("💼 Working Capital")
    c4, c5 = st.columns(2)
    c4.metric("Total AR", f"${ov.get('total_ar', 0):,.0f}", "Outstanding Receivables")
    c5.metric("Total AP", f"${ov.get('total_ap', 0):,.0f}", "Outstanding Payables", delta_color="inverse")

    st.divider()
    
    # AI Insights
    with st.spinner("Analyzing financial data..."):
        insights_map = _get_batched_insights(ai, dfs, ai_enabled).get("Overview", {})
    
    bullets = insights_map.get('bullets', [])
    raw = insights_map.get('raw')
    source = _global_insight_cache.get('source', 'Rule')

    with st.container():
        st.markdown(f"""
        <div style="background-color: #262730; padding: 15px; border-radius: 5px; border-left: 5px solid #FF4B4B;">
            <strong>&#129302; AI INSIGHTS</strong> <span style='color:#cbd5e1; font-size:0.85rem;'> (Source: {source})</span><br>
            {'<br>'.join([f'• {i}' for i in bullets])}
        </div>
        """, unsafe_allow_html=True)
        if raw:
            with st.expander("Raw LLM analysis"):
                st.text(raw)
        
    # Sales Trend Chart (Full Width)
    st.subheader("Sales Trend (L12M)")
    sales_res = FinancialAnalyzer.analyze_sales(dfs)
    if 'trend' in sales_res:
         # Use a clean Bar Chart as requested
         fig = px.bar(sales_res['trend'], x='Month', y='Revenue', 
                      color_discrete_sequence=['#00CC96'])
         
         fig.update_layout(
             height=350,  # Explicit height to prevent squashing
             xaxis_title="", 
             yaxis_title="", 
             template="plotly_dark",
             margin=dict(l=0, r=0, t=20, b=20),
             xaxis=dict(
                 tickformat="%b %Y",
                 tickmode="linear",
                 dtick="M1"
             )
         )
         st.plotly_chart(fig, use_container_width=True)

def render_sales(dfs, ai, ai_enabled=True):
    st.header("💰 Sales Performance")
    st.caption("Revenue trends and product performance analysis")
    
    # TEST: This should appear at the very top
    st.warning("🔴 TEST MARKER: If you see this, the code is executing!")
    
    # Load Data
    res = FinancialAnalyzer.analyze_sales(dfs)
    by_prod = res.get('by_product', pd.DataFrame())
    trend = res.get('trend', pd.DataFrame())
    
    # Summary Metrics
    st.subheader("📈 Key Metrics")
    if not trend.empty:
        trend_clean = trend.copy()
        trend_clean['Revenue'] = pd.to_numeric(trend_clean['Revenue'], errors='coerce')
        
        avg_sales = trend_clean['Revenue'].mean()
        max_row = trend_clean.loc[trend_clean['Revenue'].idxmax()]
        min_row = trend_clean.loc[trend_clean['Revenue'].idxmin()]
        
        max_month = pd.to_datetime(max_row['Month']).strftime('%b %Y')
        min_month = pd.to_datetime(min_row['Month']).strftime('%b %Y')
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Average Monthly Sales", f"${avg_sales:,.0f}")
        m2.metric("Highest Month", f"${max_row['Revenue']:,.0f}", delta=max_month)
        m3.metric("Lowest Month", f"${min_row['Revenue']:,.0f}", delta=min_month)
        
        st.divider()
    
    st.divider()
    st.subheader("📊 Revenue Breakdown")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("##### By Product")
        if not by_prod.empty:
            # Group small slices into "Other"
            by_prod = by_prod.sort_values('Revenue', ascending=False)
            
            # Take top 8
            top_n = 8
            if len(by_prod) > top_n:
                top_df = by_prod.iloc[:top_n].copy()
                other_rev = by_prod.iloc[top_n:]['Revenue'].sum()
                other_df = pd.DataFrame([{'Product': 'Other', 'Revenue': other_rev}])
                plot_df = pd.concat([top_df, other_df], ignore_index=True)
            else:
                plot_df = by_prod
            
            # Premium 3D Donut Chart
            from chart_styles import apply_chart_style, COLORS
            import plotly.graph_objects as go
            
            # Create vibrant color palette
            colors = ['#06B6D4', '#F59E0B', '#EF4444', '#10B981', '#8B5CF6', 
                     '#EC4899', '#F97316', '#14B8A6', '#6366F1']
            
            fig = go.Figure(data=[go.Pie(
                labels=plot_df['Product'],
                values=plot_df['Revenue'],
                hole=0.45,
                marker=dict(
                    colors=colors[:len(plot_df)],
                    line=dict(color='rgba(0,0,0,0.3)', width=2)
                ),
                textposition='inside',
                textinfo='percent+label',
                textfont=dict(size=11, color='white', family='Inter'),
                hovertemplate='<b>%{label}</b><br>Revenue: $%{value:,.0f}<br>%{percent}<extra></extra>',
                pull=[0.05] * len(plot_df),  # 3D pull effect
                opacity=0.95
            )])
            
            fig.update_layout(
                showlegend=False,
                margin=dict(t=20, b=20, l=20, r=20),
                height=400,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#F9FAFB', family='Inter')
            )
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No product data available.")
            
    with col2:
        st.markdown("##### Monthly Trend")
        if not trend.empty:
            from chart_styles import apply_chart_style, COLORS
            import plotly.graph_objects as go
            
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=trend['Month'],
                y=trend['Revenue'],
                name='Revenue',
                marker=dict(
                    color=COLORS['info'],
                    opacity=0.85,
                    line=dict(width=0)
                ),
                hovertemplate='<b>%{x|%b %Y}</b><br>Revenue: $%{y:,.0f}<extra></extra>'
            ))
            
            fig.update_layout(
                xaxis_title="",
                yaxis_title="Revenue ($)",
                xaxis=dict(tickformat="%b %Y"),
                showlegend=False,
                height=400
            )
            
            apply_chart_style(fig)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No trend data available.")
    
    # ====== NEW MONTH-ON-MONTH ANALYSIS SECTION ======
    st.divider()
    st.subheader("📈 Month-on-Month Product Performance")
    st.write("✅ **This section is rendering successfully!**")
    
    try:
        product_monthly = res.get('product_monthly', pd.DataFrame())
        product_mom_growth = res.get('product_mom_growth', pd.DataFrame())
        
        # Always show debug info for troubleshooting
        with st.expander("🔍 Data Debug Info", expanded=False):
            st.write(f"Product Monthly Data Shape: {product_monthly.shape if not product_monthly.empty else 'empty'}")
            st.write(f"Number of Months: {len(product_monthly.columns) if not product_monthly.empty else 0}")
            st.write(f"Number of Products: {len(product_monthly.index) if not product_monthly.empty else 0}")
            if not product_monthly.empty:
                st.write(f"Sample data:")
                st.dataframe(product_monthly.head())
        
        if not product_monthly.empty and len(product_monthly.columns) > 1:
            # Select visualization type
            viz_type = st.radio(
                "View:",
                ["Monthly Sales by Product", "MoM Growth % Heatmap"],
                horizontal=True,
                key="mom_viz_type"
            )
            
            if viz_type == "Monthly Sales by Product":
                # Line chart showing each product's monthly sales
                import plotly.graph_objects as go
                from chart_styles import apply_chart_style
                
                fig = go.Figure()
                
                # Color palette for products
                colors = ['#06B6D4', '#F59E0B', '#EF4444', '#10B981', '#8B5CF6', 
                         '#EC4899', '#F97316', '#14B8A6', '#6366F1', '#A78BFA']
                
                # Get top 8 products by total revenue
                top_products = product_monthly.sum(axis=1).nlargest(8).index
                
                for idx, product in enumerate(top_products):
                    color = colors[idx % len(colors)]
                    fig.add_trace(go.Scatter(
                        x=[col.strftime('%b %Y') for col in product_monthly.columns],
                        y=product_monthly.loc[product],
                        name=product,
                        mode='lines+markers',
                        line=dict(color=color, width=2.5),
                        marker=dict(size=7, color=color),
                        hovertemplate='<b>' + product + '</b><br>%{x}<br>Revenue: $%{y:,.0f}<extra></extra>'
                    ))
                
                fig.update_layout(
                    xaxis_title="",
                    yaxis_title="Revenue ($)",
                    height=450,
                    hovermode='x unified',
                    legend=dict(
                        orientation="v",
                        yanchor="top",
                        y=1,
                        xanchor="left",
                        x=1.02
                    )
                )
                
                apply_chart_style(fig)
                st.plotly_chart(fig, use_container_width=True)
                
            else:
                # Heatmap showing MoM growth percentages
                if not product_mom_growth.empty:
                    import plotly.graph_objects as go
                    from chart_styles import apply_chart_style
                    
                    # Get top 10 products by total revenue
                    top_products = product_monthly.sum(axis=1).nlargest(10).index
                    growth_subset = product_mom_growth.loc[top_products]
                    
                    # Format month labels
                    month_labels = [col.strftime('%b %Y') for col in growth_subset.columns]
                    
                    # Create heatmap
                    fig = go.Figure(data=go.Heatmap(
                        z=growth_subset.values,
                        x=month_labels,
                        y=growth_subset.index,
                        colorscale=[
                            [0, '#EF4444'],      # Red for negative
                            [0.5, '#F3F4F6'],    # Light gray for zero
                            [1, '#10B981']       # Green for positive
                        ],
                        zmid=0,
                        text=growth_subset.values.round(1),
                        texttemplate='%{text}%',
                        textfont={"size": 10},
                        colorbar=dict(
                            title="Growth %",
                            titleside="right",
                            ticksuffix="%"
                        ),
                        hovertemplate='<b>%{y}</b><br>%{x}<br>MoM Growth: %{z:.1f}%<extra></extra>'
                    ))
                    
                    fig.update_layout(
                        xaxis_title="",
                        yaxis_title="",
                        height=400,
                        yaxis=dict(autorange='reversed')
                    )
                    
                    apply_chart_style(fig)
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Summary insights
                    col_a, col_b, col_c = st.columns(3)
                    
                    # Find best and worst performers in latest month
                    latest_month = product_mom_growth.columns[-1]
                    latest_growth = product_mom_growth[latest_month].sort_values(ascending=False)
                    
                    # Filter out zero or NaN values
                    latest_growth_clean = latest_growth[latest_growth.notna() & (latest_growth != 0)]
                    
                    if len(latest_growth_clean) > 0:
                        best_product = latest_growth_clean.index[0]
                        best_growth = latest_growth_clean.iloc[0]
                        
                        worst_product = latest_growth_clean.index[-1]
                        worst_growth = latest_growth_clean.iloc[-1]
                        
                        avg_growth = latest_growth_clean.mean()
                        
                        col_a.metric("Top Performer", best_product, f"+{best_growth:.1f}%")
                        col_b.metric("Average MoM Growth", f"{avg_growth:.1f}%")
                        col_c.metric("Needs Attention", worst_product, f"{worst_growth:.1f}%", delta_color="inverse")
                else:
                    st.info("Insufficient data for MoM growth analysis.")
        else:
            st.info("Insufficient monthly data for product-wise trend analysis. Need at least 2 months of data.")
            
    except Exception as e:
        st.error(f"Error rendering MoM analysis: {str(e)}")
        import traceback
        with st.expander("Error Details"):
            st.code(traceback.format_exc())
    
    # Custom Info Box for Sales Insights
    st.divider()
    insights_map = _get_batched_insights(ai, dfs, ai_enabled).get("Sales Trends", {})
    bullets = insights_map.get('bullets', [])
    raw = insights_map.get('raw')
    source = _global_insight_cache.get('source', 'Rule')

    # Custom Info Box for Sales Insights
    content = " | ".join(bullets)
    src_label = f"<span style='color:#cbd5e1; font-size:0.85rem;'>(Source: {source})</span>"
    st.markdown(f"""
    <div style="background-color: rgba(67, 97, 238, 0.1); padding: 12px 16px; border-radius: 8px; border: 1px solid rgba(67, 97, 238, 0.3); color: #F8FAFC; font-size: 0.95rem; margin-bottom: 20px;">
        <span style="color: #60A5FA; font-weight: 600;">&#8505; TREND ANALYSIS:</span> {content} {src_label}
    </div>
    """, unsafe_allow_html=True)
    if raw:
        with st.expander("Raw LLM analysis (Sales Trends)"):
            st.text(raw)

def render_ar(dfs, ai, ai_enabled=True):
    st.header("📥 Accounts Receivable Aging")
    st.caption("Track outstanding customer invoices and collection status")
    
    if not dfs or 'AR' not in dfs:
        st.info("💡 AR data not available. Upload data with 'AR' sheet.")
        return
    
    res = FinancialAnalyzer.analyze_ar(dfs)
    
    # Quick Summary Metric
    st.metric("💵 Total Outstanding AR", f"${res.get('total_ar', 0):,.2f}", help="Total amount owed by customers")
    st.divider()
    
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Aging Breakdown")
        aging_df = res['aging_table']
        if not aging_df.empty:
            # Colorful bar chart for aging
            fig = px.bar(aging_df, x='AgingBucket', y='Amount', 
                         color='AgingBucket', 
                         title="Aging by Period",
                         color_discrete_sequence=px.colors.sequential.RdBu,
                         template="plotly_dark")
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No aging data.")
            
    with c2:
        st.markdown("##### Top Delinquent Accounts")
        details = res['details']
        if not details.empty:
            # Horizontal bar for top customers
            fig = px.bar(details.head(8), y='Customer', x='Amount', orientation='h',
                         title="Top Outstanding Invoices",
                         color='Amount', color_continuous_scale='Reds',
                         template="plotly_dark")
            fig.update_layout(yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No details available.")
    
    st.divider()
    
    # AI Insights (AR Collections)
    insights_map = _get_batched_insights(ai, dfs, ai_enabled).get("AR Collections", {})
    bullets = insights_map.get('bullets', [])
    raw = insights_map.get('raw')
    source = _global_insight_cache.get('source', 'Rule')

    with st.container():
        st.markdown(f"""
        <div style="background-color: #262730; padding: 15px; border-radius: 5px; border-left: 5px solid #AB63FA;">
            <strong>&#129302; AI AR ANALYSIS</strong> <span style='color:#cbd5e1; font-size:0.85rem;'> (Source: {source})</span><br>
            {'<br>'.join([f'• {i}' for i in bullets])}
        </div>
        """, unsafe_allow_html=True)
    if raw:
        with st.expander("Raw LLM analysis (AR)"):
            st.text(raw)
    
    with st.expander("View Detailed Aging Table"):
        st.dataframe(res['aging_table'].style.format({'Amount': '${:,.2f}'}))

def render_ap(dfs, ai, ai_enabled=True):
    st.header("💸 Accounts Payable Management")
    st.caption("Monitor vendor payments and upcoming obligations")
    
    res = FinancialAnalyzer.analyze_ap(dfs)
    
    st.subheader("📊 Summary Metrics")
    k1, k2, k3 = st.columns(3)
    k1.metric("Total Payables Open", f"${res['total_open']:,.2f}")
    k2.metric("Due Next 30 Days", f"${res['upcoming_30d']:,.2f}", help="Requires immediate attention")
    k3.metric("Active Vendors", f"{len(res['vendors'])}")
    
    st.divider()
    
    c1, c2 = st.columns(2)
    
    with c1:
         st.subheader("Top Vendors Owed")
         vendors = res['vendors']
         if not vendors.empty:
             fig = px.bar(vendors.head(8), y='Vendor', x='Amount', orientation='h',
                          color='Amount', color_continuous_scale='Viridis',
                          template="plotly_dark")
             fig.update_layout(yaxis={'categoryorder':'total ascending'})
             st.plotly_chart(fig, use_container_width=True)
    
    with c2:
        st.markdown("##### Payment Distribution")
        if not vendors.empty:
             top_v = vendors.head(5)
             other_amt = vendors.iloc[5:]['Amount'].sum()
             plot_df = pd.concat([top_v, pd.DataFrame([{'Vendor': 'Other', 'Amount': other_amt}])], ignore_index=True)
             fig = px.pie(plot_df, values='Amount', names='Vendor', hole=0.4, title="Payables Distribution", template="plotly_dark")
             st.plotly_chart(fig, use_container_width=True)

        # AI Insights (AP Management)
        insights_map = _get_batched_insights(ai, dfs, ai_enabled).get("AP Management", {})
        bullets = insights_map.get('bullets', [])
        raw = insights_map.get('raw')
        source = _global_insight_cache.get('source', 'Rule')
        with st.container():
            st.markdown(f"""
            <div style="background-color: #262730; padding: 15px; border-radius: 5px; border-left: 5px solid #EF553B;">
                <strong>&#129302; AI AP ANALYSIS</strong> <span style='color:#cbd5e1; font-size:0.85rem;'> (Source: {source})</span><br>
                {'<br>'.join([f'• {i}' for i in bullets])}
            </div>
            """, unsafe_allow_html=True)
            if raw:
                with st.expander("Raw LLM analysis (AP)"):
                    st.text(raw)

def render_cash(dfs, ai, ai_enabled=True):
    st.header("💵 Cash Flow Statement Analysis")
    st.caption("QuickBooks Statement of Cash Flows - Indirect Method")
    
    # Use the Cash Flow Statement analyzer
    res = FinancialAnalyzer.analyze_cash_flow_statement(dfs)
    
    if res:
        # Key Metrics in columns
        st.subheader("📊 Cash Flow Summary")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Operating Cash Flow", f"${res['operating_cf']:,.0f}", 
                     delta="Healthy" if res['operating_cf'] > 0 else "Negative",
                     delta_color="normal" if res['operating_cf'] > 0 else "inverse")
        
        with col2:
            st.metric("Investing Cash Flow", f"${res['investing_cf']:,.0f}",
                     help="Negative = Investments in assets")
        
        with col3:
            st.metric("Financing Cash Flow", f"${res['financing_cf']:,.0f}",
                     help="Loans, equity, dividends")
        
        with col4:
            st.metric("Net Cash Change", f"${res['net_cash_change']:,.0f}",
                     delta="Increasing" if res['net_cash_change'] > 0 else "Decreasing",
                     delta_color="normal" if res['net_cash_change'] > 0 else "inverse")
        
        st.divider()
        
        # Free Cash Flow Highlight
        fcf_col1, fcf_col2 = st.columns(2)
        with fcf_col1:
            st.metric("💰 Free Cash Flow (FCF)", f"${res['free_cash_flow']:,.0f}",
                     help="Operating CF + Investing CF = Cash available after investments")
            fcf_quality = "Excellent" if res['free_cash_flow'] > 50000 else "Good" if res['free_cash_flow'] > 0 else "Negative"
            st.info(f"FCF Quality: **{fcf_quality}**")
        
        with fcf_col2:
            st.metric("Net Income (Accrual)", f"${res['net_income']:,.0f}",
                     help="From P&L statement")
            conversion = (res['operating_cf'] / res['net_income'] * 100) if res['net_income'] != 0 else 0
            st.info(f"Cash Conversion: **{conversion:.1f}%** (Operating CF / Net Income)")
        
        st.divider()
        
        # Operating Activities Breakdown
        st.subheader("Operating Activities Breakdown")
        st.markdown("""
        *Operating Cash Flow uses the **Indirect Method**: starts with Net Income and adjusts for non-cash items and working capital changes.*
        """)
        
        # Get operating items from analysis result
        operating_items = res.get('operating_items', pd.DataFrame())
        
        if not operating_items.empty:
            # Show key operating components
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("##### Starting Point")
                net_income_row = operating_items[operating_items['Line_Item'].str.contains('Net Income', case=False, na=False)]
                if not net_income_row.empty:
                    ni_amount = net_income_row['Amount'].iloc[0]
                    st.metric("Net Income (Accrual Basis)", f"${ni_amount:,.0f}")
                
                st.markdown("##### Add Back: Non-Cash Expenses")
                depreciation = operating_items[operating_items['Line_Item'].str.contains('Depreciation|Amortization', case=False, na=False)]['Amount'].sum()
                if depreciation != 0:
                    st.info(f"💡 Depreciation/Amortization: **${depreciation:,.0f}**  \n(Reduced Net Income but didn't use cash)")
            
            with col2:
                st.markdown("##### Working Capital Changes")
                ar_change = operating_items[operating_items['Line_Item'].str.contains('Accounts Receivable|A/R', case=False, na=False)]['Amount'].sum()
                ap_change = operating_items[operating_items['Line_Item'].str.contains('Accounts Payable|A/P', case=False, na=False)]['Amount'].sum()
                
                if ar_change != 0:
                    if ar_change < 0:
                        st.warning(f"📉 A/R Increased: **${abs(ar_change):,.0f}**  \n(Sales made but cash not collected)")
                    else:
                        st.success(f"📈 A/R Decreased: **${ar_change:,.0f}**  \n(Collected from customers)")
                
                if ap_change != 0:
                    if ap_change > 0:
                        st.success(f"📈 A/P Increased: **${ap_change:,.0f}**  \n(Received goods but haven't paid yet)")
                    else:
                        st.warning(f"📉 A/P Decreased: **${abs(ap_change):,.0f}**  \n(Paid off suppliers)")
            
            # Show full operating details in expander
            with st.expander("📋 View All Operating Activity Adjustments"):
                operating_display = operating_items[operating_items['Amount'] != 0].copy()
                if not operating_display.empty:
                    operating_display['Amount'] = operating_display['Amount'].apply(lambda x: f"${x:,.0f}")
                    st.dataframe(operating_display[['Line_Item', 'Amount']], hide_index=True, use_container_width=True)
        else:
            st.info("Operating activities breakdown not available")
        
        st.divider()
        
        # Waterfall Chart - Cash Flow Components
        st.subheader("Cash Flow Waterfall")
        import plotly.graph_objects as go
        from chart_styles import apply_chart_style
        
        fig_waterfall = go.Figure(go.Waterfall(
            name="Cash Flow",
            orientation="v",
            measure=["relative", "relative", "relative", "total"],
            x=["Operating", "Investing", "Financing", "Net Change"],
            textposition="outside",
            y=[res['operating_cf'], res['investing_cf'], res['financing_cf'], res['net_cash_change']],
            connector={"line": {"color": "rgb(63, 63, 63)"}},
            decreasing={"marker": {"color": "#EF4444"}},
            increasing={"marker": {"color": "#10B981"}},
            totals={"marker": {"color": "#3B82F6"}},
            text=[f"${res['operating_cf']:,.0f}", f"${res['investing_cf']:,.0f}", 
                  f"${res['financing_cf']:,.0f}", f"${res['net_cash_change']:,.0f}"]
        ))
        
        fig_waterfall.update_layout(
            title="Cash Flow Components",
            showlegend=False,
            height=400,
            yaxis=dict(title="Amount ($)")
        )
        
        apply_chart_style(fig_waterfall)
        st.plotly_chart(fig_waterfall, use_container_width=True)
        
        # Top Cash Sources and Uses
        st.subheader("Actual Cash Transactions (Investing & Financing Activities Only)")
        c1, c2 = st.columns(2)
        
        with c1:
            st.markdown("##### 💸 Top Cash Payments")
            if not res['top_outflows'].empty:
                outflow_display = res['top_outflows'][['Line_Item', 'Amount']].copy()
                outflow_display['Amount'] = outflow_display['Amount'].apply(lambda x: f"${abs(x):,.0f}")
                st.dataframe(outflow_display, hide_index=True, use_container_width=True)
            else:
                st.info("No major cash payments found")
        
        with c2:
            st.markdown("##### 💰 Top Cash Receipts")
            if not res['top_inflows'].empty:
                inflow_display = res['top_inflows'][['Line_Item', 'Amount']].copy()
                inflow_display['Amount'] = inflow_display['Amount'].apply(lambda x: f"${x:,.0f}")
                st.dataframe(inflow_display, hide_index=True, use_container_width=True)
            else:
                st.info("No major cash receipts found")
        
        st.caption("Note: Showing only Investing (e.g., equipment purchases) and Financing (e.g., loans, equity) activities. Operating section excluded to avoid showing non-cash reconciliation items like A/R, A/P, and depreciation adjustments.")
        
        # AI Insights for Cash Flow
        st.divider()
        insights_map = _get_batched_insights(ai, dfs, ai_enabled).get("Cash Flow Statement", {})
        bullets = insights_map.get('bullets', [])
        raw = insights_map.get('raw')
        source = _global_insight_cache.get('source', 'Rule')
        
        with st.container():
            st.markdown(f"""
            <div style="background-color: #262730; padding: 15px; border-radius: 5px; border-left: 5px solid #10B981;">
                <strong>🤖 AI CASH FLOW ANALYSIS</strong> <span style='color:#cbd5e1; font-size:0.85rem;'> (Source: {source})</span><br>
                {'<br>'.join([f'• {i}' for i in bullets])}
            </div>
            """, unsafe_allow_html=True)
        
        if raw:
            with st.expander("Raw LLM analysis (Cash Flow)"):
                st.text(raw)
    
    else:
        st.warning("⚠️ No Cash Flow Statement data available")
        st.info("💡 **How to fix:** Ensure your Excel file contains a 'Cash flow' sheet with the QuickBooks Statement of Cash Flows format.")

def render_profit(dfs, ai, ai_enabled=True):
    st.header("📊 Profit & Loss Analysis")
    st.caption("Income statement with operating and net profit metrics")
    
    res = FinancialAnalyzer.analyze_profit(dfs)
    pnl = res.get('monthly_pnl', pd.DataFrame())
    ytd = res.get('metrics', {})
    
    if not pnl.empty:
        # Metrics
        st.subheader("💰 YTD Performance")
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Operating Income", f"${ytd.get('ytd_op_income', 0):,.0f}")
        m2.metric("Operating Expense", f"${ytd.get('ytd_op_expense', 0):,.0f}", delta_color="inverse")
        m3.metric("Net Operating Profit", f"${ytd.get('ytd_net_op_profit', 0):,.0f}", f"{ytd.get('op_margin', 0):.1f}% Margin")
        m4.metric("Total Net Profit", f"${ytd.get('ytd_net_profit', 0):,.0f}", f"{ytd.get('net_margin', 0):.1f}% Margin")
        
        st.divider()
        st.subheader("📈 Monthly Trends")
        
        from chart_styles import apply_chart_style, COLORS
        import plotly.graph_objects as go
        
        # Create grouped bar chart
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=pnl['Month'],
            y=pnl['OperatingIncome'],
            name='Operating Income',
            marker=dict(color=COLORS['success'], opacity=0.85),
            hovertemplate='<b>%{x|%b %Y}</b><br>Income: $%{y:,.0f}<extra></extra>'
        ))
        
        fig.add_trace(go.Bar(
            x=pnl['Month'],
            y=pnl['OperatingExpense'],
            name='Operating Expense',
            marker=dict(color=COLORS['danger'], opacity=0.85),
            hovertemplate='<b>%{x|%b %Y}</b><br>Expense: $%{y:,.0f}<extra></extra>'
        ))
        
        fig.update_layout(
            title="Operating Income vs Operating Expenses",
            xaxis=dict(tickformat="%b %Y"),
            barmode='group',
            height=400,
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
        )
        
        apply_chart_style(fig)
        st.plotly_chart(fig, use_container_width=True)
        
        # Detailed Table
        st.subheader("Monthly P&L Breakdown")
        
        # Format for display
        pnl_display = pnl.copy()
        if 'Month' in pnl_display.columns:
            pnl_display['Month'] = pd.to_datetime(pnl_display['Month']).dt.strftime('%b %Y')
        
        # Select and Rename columns for clarity
        cols_to_show = ['Month', 'OperatingIncome', 'OperatingExpense', 'NetOperatingProfit', 'OtherIncome', 'OtherExpense', 'NetProfit', 'Margin']
        pnl_display = pnl_display[cols_to_show]
        
        st.dataframe(pnl_display.style.format({
            'OperatingIncome': '${:,.0f}', 
            'OperatingExpense': '${:,.0f}', 
            'NetOperatingProfit': '${:,.0f}',
            'OtherIncome': '${:,.0f}',
            'OtherExpense': '${:,.0f}', 
            'NetProfit': '${:,.0f}', 
            'Margin': '{:.1f}%'
        }))
        
        # Categorized Statement
        st.subheader("Detailed Financial Statement (Categorized)")
        detailed_pivot = res.get('detailed_pivot')
        if detailed_pivot is not None and not detailed_pivot.empty:
             st.dataframe(detailed_pivot.style.format("${:,.0f}"))
        else:
            st.info("Detailed categorization unavailable.")
            
        # Insights Setup
        insights_map = _get_batched_insights(ai, dfs, ai_enabled).get("Profitability", {})
        bullets = insights_map.get('bullets', [])
        raw = insights_map.get('raw')
        source = _global_insight_cache.get('source', 'Rule')
        with st.container():
             st.markdown(f"""
             <div style="background-color: #262730; padding: 15px; border-radius: 5px; border-left: 5px solid #FF4B4B;">
                 <strong>&#129302; AI ANALYSIS (P&L)</strong> <span style='color:#cbd5e1; font-size:0.85rem;'> (Source: {source})</span><br>
                 {'<br>'.join([f'• {i}' for i in bullets])}
             </div>
             """, unsafe_allow_html=True)
             if raw:
                 with st.expander("Raw LLM analysis (P&L)"):
                     st.text(raw)
        
    else:
        st.info("No P&L data derived.")

def render_forecast(dfs, ai, ai_enabled=True):
    st.header("🔮 Income Forecast (Beta)")
    st.caption("Predictive analytics based on historical trends")
    
    st.info("📊 **Methodology:** Using last 6 months average growth rate (capped at ±20%) to project next 3 months")
    
    res = FinancialAnalyzer.analyze_forecast(dfs)
    
    if res and res.get('forecast') is not None and not res['forecast'].empty:
        history = res['history']
        forecast = res['forecast']
        growth_rate = res['growth_rate']
        
        # Combine for Charting
        # We want to connect the lines, so add the last historical point to forecast
        last_hist = history.iloc[-1]
        connect_point = pd.DataFrame([{
            'Month': last_hist['Month'], 
            'Revenue': last_hist['Revenue'], 
            'Type': 'Forecast' # Overlap point
        }])
        
        # chart_data = pd.concat([history, connect_point, forecast])
        # Actually easier to just plot them as two traces
        
        # Display Growth Metric
        c1, c2 = st.columns(2)
        c1.metric("Historical Trend", "L6M Average")
        c2.metric("Projected Growth Rate", f"{growth_rate*100:.1f}%", help="Capped at ±20% for realism")
        
        # Chart
        # Concatenate for single source
        combined = pd.concat([history, forecast], ignore_index=True)
        
        from chart_styles import apply_chart_style, COLORS, get_line_config
        import plotly.graph_objects as go
        
        fig = go.Figure()
        
        # Actual line (solid)
        fig.add_trace(go.Scatter(
            x=history['Month'],
            y=history['Revenue'],
            name='Actual',
            mode='lines+markers',
            line=dict(color=COLORS['success'], width=3, shape='spline'),
            marker=dict(size=6, color=COLORS['success']),
            hovertemplate='<b>%{x|%b %Y}</b><br>Actual: $%{y:,.0f}<extra></extra>'
        ))
        
        # Forecast line (dashed)
        fig.add_trace(go.Scatter(
            x=forecast['Month'],
            y=forecast['Revenue'],
            name='Forecast',
            mode='lines+markers',
            line=dict(color=COLORS['warning'], width=3, dash='dash', shape='spline'),
            marker=dict(size=6, color=COLORS['warning'], symbol='diamond'),
            hovertemplate='<b>%{x|%b %Y}</b><br>Forecast: $%{y:,.0f}<extra></extra>'
        ))
        
        fig.update_layout(
            title="Projected Operating Income (Next 3 Months)",
            xaxis=dict(tickformat="%b %Y"),
            yaxis=dict(title="Revenue ($)"),
            height=400,
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
        )
        
        apply_chart_style(fig)
        st.plotly_chart(fig, use_container_width=True)
        
        # Table
        st.subheader("Forecast Values")
        f_display = forecast.copy()
        if 'Month' in f_display.columns:
             f_display['Month'] = pd.to_datetime(f_display['Month']).dt.strftime('%b %Y')
             
        st.dataframe(f_display[['Month', 'Revenue']].style.format({'Revenue': '${:,.0f}'}))
        
        # AI Insights (Forecast)
        insights_map = _get_batched_insights(ai, dfs, ai_enabled).get("Forecast", {})
        bullets = insights_map.get('bullets', [])
        raw = insights_map.get('raw')
        source = _global_insight_cache.get('source', 'Rule')
        with st.container():
            st.markdown(f"""
            <div style="background-color: #262730; padding: 15px; border-radius: 5px; border-left: 5px solid #AB63FA;">
                <strong>&#129302; AI FORECAST ANALYSIS</strong> <span style='color:#cbd5e1; font-size:0.85rem;'> (Source: {source})</span><br>
                {'<br>'.join([f'• {i}' for i in bullets])}
            </div>
            """, unsafe_allow_html=True)
            if raw:
                with st.expander("Raw LLM analysis (Forecast)"):
                    st.text(raw)
             
    else:
        st.warning("Insufficient data to generate a forecast. Need at least 2 months of Operating Income data.")

def render_spending(dfs, ai, ai_enabled=True):
    st.header("💳 Spending Analysis")
    st.caption("Expense trends and cost driver analysis")
    
    res = FinancialAnalyzer.analyze_spending(dfs)
    
    if res:
        # Summary Metrics
        st.subheader("📊 Spending Overview")
        monthly = res['monthly']
        if not monthly.empty:
            monthly_clean = monthly.copy()
            monthly_clean['Revenue'] = pd.to_numeric(monthly_clean['Revenue'], errors='coerce')
            
            avg_spend = monthly_clean['Revenue'].mean()
            max_row = monthly_clean.loc[monthly_clean['Revenue'].idxmax()]
            min_row = monthly_clean.loc[monthly_clean['Revenue'].idxmin()]
            
            max_month = pd.to_datetime(max_row['Month']).strftime('%b %Y')
            min_month = pd.to_datetime(min_row['Month']).strftime('%b %Y')
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Average Monthly Spending", f"${avg_spend:,.0f}")
            m2.metric("Highest Month", f"${max_row['Revenue']:,.0f}", delta=max_month)
            m3.metric("Lowest Month", f"${min_row['Revenue']:,.0f}", delta=min_month)
            
            st.divider()
        
        # 1. Monthly Trend Bar Chart
        st.subheader("Total Monthly Spending")
        
        from chart_styles import apply_chart_style, COLORS
        import plotly.graph_objects as go
        
        fig_trend = go.Figure()
        fig_trend.add_trace(go.Bar(
            x=monthly['Month'],
            y=monthly['Revenue'],
            name='Total Spending',
            marker=dict(
                color=COLORS['danger'],
                opacity=0.85,
                line=dict(width=0)
            ),
            hovertemplate='<b>%{x|%b %Y}</b><br>Spending: $%{y:,.0f}<extra></extra>'
        ))
        
        fig_trend.update_layout(
            title="Total Outflow Trend (Operating + Other)",
            xaxis=dict(tickformat="%b %Y"),
            yaxis=dict(title="Amount ($)"),
            showlegend=False,
            height=400
        )
        
        apply_chart_style(fig_trend)
        st.plotly_chart(fig_trend, use_container_width=True)
        
        # Split layout for Top 5
        st.subheader("Top Expense Drivers")
        c1, c2 = st.columns(2)
        
        # 2. Top 5 Categories (Premium 3D Donut)
        with c1:
            st.markdown("##### Highest Spending Accounts (YTD)")
            top_5 = res['top_5_ytd']
            
            import plotly.graph_objects as go
            
            # Warm color palette for expenses
            expense_colors = ['#EF4444', '#F59E0B', '#EC4899', '#F97316', '#DC2626']
            
            fig_donut = go.Figure(data=[go.Pie(
                labels=top_5['Product'],
                values=top_5['Revenue'],
                hole=0.45,
                marker=dict(
                    colors=expense_colors[:len(top_5)],
                    line=dict(color='rgba(0,0,0,0.3)', width=2)
                ),
                textposition='inside',
                textinfo='percent+label',
                textfont=dict(size=10, color='white', family='Inter'),
                hovertemplate='<b>%{label}</b><br>Spending: $%{value:,.0f}<br>%{percent}<extra></extra>',
                pull=[0.05] * len(top_5),
                opacity=0.95
            )])
            
            fig_donut.update_layout(
                showlegend=False,
                margin=dict(t=10, b=10, l=10, r=10),
                height=350,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#F9FAFB', family='Inter')
            )
            
            st.plotly_chart(fig_donut, use_container_width=True)
            
        # 3. Top 5 Trend (Line)
        with c2:
            st.markdown("##### Top 5 Accounts Trend (MoM)")
            top_trend = res['top_5_trend']
            fig_line = px.line(top_trend, x='Month', y='Revenue', color='Product',
                               markers=True,
                               template="plotly_dark")
            fig_line.update_layout(xaxis=dict(tickformat="%b"))
            st.plotly_chart(fig_line, use_container_width=True)

        # AI Insights (Spending)
        insights_map = _get_batched_insights(ai, dfs, ai_enabled).get("Spending", {})
        bullets = insights_map.get('bullets', [])
        raw = insights_map.get('raw')
        source = _global_insight_cache.get('source', 'Rule')
        with st.container():
            st.markdown(f"""
            <div style="background-color: #262730; padding: 15px; border-radius: 5px; border-left: 5px solid #EF553B;">
                <strong>&#129302; AI SPEND ANALYSIS</strong> <span style='color:#cbd5e1; font-size:0.85rem;'> (Source: {source})</span><br>
                {'<br>'.join([f'• {i}' for i in bullets])}
            </div>
            """, unsafe_allow_html=True)
            if raw:
                with st.expander("Raw LLM analysis (Spending)"):
                    st.text(raw)
    else:
        st.info("No spending data available.")
