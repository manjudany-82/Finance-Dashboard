
import streamlit as st
import pandas as pd
import plotly.express as px
from analysis_modes import FinancialAnalyzer
from forecast_engine import ForecastEngine

def render_overview(dfs, ai):
    st.header("Executive Overview")
    
    # --- HEADER (YTD & Balance Sheet) ---
    c1, c2, c3, c4, c5 = st.columns(5)
    ov = FinancialAnalyzer.analyze_overview(dfs)
    
    c1.metric("YTD Sales", f"${ov.get('ytd_sales', 0):,.0f}")
    c2.metric("YTD Expenses", f"${ov.get('ytd_expense', 0):,.0f}", delta_color="inverse")
    
    np = ov.get('net_profit', 0)
    c3.metric("Net Profit", f"${np:,.0f}", f"{ov.get('net_profit_margin', 0):.1f}% Margin")
    
    c4.metric("Total AR", f"${ov.get('total_ar', 0):,.0f}", "Open Invoices")
    c5.metric("Total AP", f"${ov.get('total_ap', 0):,.0f}", "Open Bills", delta_color="inverse")

    st.markdown("---")
    
    # AI Insights
    insights = ai.get_insights("Overview", ov) if ai.model else ai.generate_fallback_insights("Overview", ov)
    
    with st.container():
        st.markdown(f"""
        <div style="background-color: #262730; padding: 15px; border-radius: 5px; border-left: 5px solid #FF4B4B;">
            <strong>&#129302; AI INSIGHTS:</strong><br>
            {'<br>'.join([f'• {i}' for i in insights])}
        </div>
        """, unsafe_allow_html=True)
        
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

def render_sales(dfs, ai):
    st.header("Sales Performance")
    
    # Load Data
    res = FinancialAnalyzer.analyze_sales(dfs)
    by_prod = res.get('by_product', pd.DataFrame())
    trend = res.get('trend', pd.DataFrame())
    
    # Summary Metrics
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
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Revenue by Product")
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
        st.subheader("Revenue Trend")
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
        
    
    # Custom Info Box for Sales Insights
    # Now passing raw 'res' object, not str(res)
    insights = ai.get_insights("Sales Trends", res) if ai.model else ai.generate_fallback_insights("Sales Trends", res)
    
    # Custom Info Box for Sales Insights
    content = " | ".join(insights)
    st.markdown(f"""
    <div style="background-color: rgba(67, 97, 238, 0.1); padding: 12px 16px; border-radius: 8px; border: 1px solid rgba(67, 97, 238, 0.3); color: #F8FAFC; font-size: 0.95rem; margin-bottom: 20px;">
        <span style="color: #60A5FA; font-weight: 600;">&#8505; TREND ANALYSIS:</span> {content}
    </div>
    """, unsafe_allow_html=True)

def render_ar(dfs, ai):
    st.header("Accounts Receivable Aging")
    res = FinancialAnalyzer.analyze_ar(dfs)
    
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
        st.subheader("Top Delinquent Accounts")
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

    # Metric Strip
    st.metric("Total Outstanding AR", f"${res.get('total_ar', 0):,.2f}", "Critical", delta_color="inverse")
    
    # Insights
    insights = ai.get_insights("AR Collections", res) if ai.model else ai.generate_fallback_insights("AR Collections", res)
    with st.container():
        st.markdown(f"""
        <div style="background-color: #262730; padding: 15px; border-radius: 5px; border-left: 5px solid #FF4B4B;">
            <strong>&#129302; AI ANALYSIS (AR):</strong><br>
            {'<br>'.join([f'• {i}' for i in insights])}
        </div>
        """, unsafe_allow_html=True)
    
    with st.expander("View Detailed Aging Table"):
        st.dataframe(res['aging_table'].style.format({'Amount': '${:,.2f}'}))

def render_ap(dfs, ai):
    st.header("Accounts Payable Management")
    res = FinancialAnalyzer.analyze_ap(dfs)
    
    k1, k2, k3 = st.columns(3)
    k1.metric("Total Payables Open", f"${res['total_open']:,.2f}")
    k2.metric("Due Next 30 Days", f"${res['upcoming_30d']:,.2f}", delta="-High Priority", delta_color="inverse")
    k3.metric("Vendors Count", f"{len(res['vendors'])}")
    
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
        st.subheader("Payment Schedule")
        if not vendors.empty:
             top_v = vendors.head(5)
             other_amt = vendors.iloc[5:]['Amount'].sum()
             plot_df = pd.concat([top_v, pd.DataFrame([{'Vendor': 'Other', 'Amount': other_amt}])], ignore_index=True)
             fig = px.pie(plot_df, values='Amount', names='Vendor', hole=0.4, title="Payables Distribution", template="plotly_dark")
             st.plotly_chart(fig, use_container_width=True)

    # Insights
    insights = ai.get_insights("AP Management", res) if ai.model else ai.generate_fallback_insights("AP Management", res)
    with st.container():
         st.markdown(f"""
         <div style="background-color: #262730; padding: 15px; border-radius: 5px; border-left: 5px solid #FF4B4B;">
             <strong>&#129302; AI ANALYSIS (AP):</strong><br>
             {'<br>'.join([f'• {i}' for i in insights])}
         </div>
         """, unsafe_allow_html=True)

def render_cash(dfs, ai):
    st.header("Cash Flow & Runway")
    res = FinancialAnalyzer.analyze_cash(dfs)
    
    st.metric("Estimated Runway", f"{res['runway_months']:.1f} Months", "Critical" if res['runway_months'] < 6 else "Stable")
    
    st.plotly_chart(px.line(res['daily_trend'], x='Date', y='Balance', title="Daily Cash Balance", template="plotly_dark"), use_container_width=True)
    
    # Forecast Overlay
    fe_res = ForecastEngine.run_cash_forecast(dfs.get('Cash'))
    if fe_res is not None:
         df_fc, slope = fe_res
         st.subheader(f"Cash Forecast (Next 3 Months) - Trend Slope: {slope:.2f}")
         fig_fc = px.line(df_fc, x='Date', y='Balance', color='Type', template="plotly_dark")
         st.plotly_chart(fig_fc, use_container_width=True)

    # Insights
    insights = ai.get_insights("Cash Flow", res) if ai.model else ai.generate_fallback_insights("Cash Flow", res)
    with st.container():
         st.markdown(f"""
         <div style="background-color: #262730; padding: 15px; border-radius: 5px; border-left: 5px solid #FF4B4B;">
             <strong>&#129302; AI ANALYSIS (CASH):</strong><br>
             {'<br>'.join([f'• {i}' for i in insights])}
         </div>
         """, unsafe_allow_html=True)

def render_profit(dfs, ai):
    st.header("Profit & Loss Analysis")
    res = FinancialAnalyzer.analyze_profit(dfs)
    pnl = res.get('monthly_pnl', pd.DataFrame())
    ytd = res.get('metrics', {})
    
    if not pnl.empty:
        # Metrics
        st.subheader("YTD Performance (Fiscal Year)")
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Operating Income", f"${ytd.get('ytd_op_income', 0):,.0f}")
        m2.metric("Operating Expense", f"${ytd.get('ytd_op_expense', 0):,.0f}", delta_color="inverse")
        m3.metric("Net Operating Profit", f"${ytd.get('ytd_net_op_profit', 0):,.0f}", f"{ytd.get('op_margin', 0):.1f}% Margin")
        m4.metric("Total Net Profit", f"${ytd.get('ytd_net_profit', 0):,.0f}", f"{ytd.get('net_margin', 0):.1f}% Margin")
        
        st.markdown("---")
        st.markdown("### Operating Performance (Month-on-Month)")
        
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
        insights = ai.get_insights("Profitability", str(res)) if ai.model else ai.generate_fallback_insights("Profitability", res)
        with st.container():
             st.markdown(f"""
             <div style="background-color: #262730; padding: 15px; border-radius: 5px; border-left: 5px solid #FF4B4B;">
                 <strong>&#129302; AI ANALYSIS (P&L):</strong><br>
                 {'<br>'.join([f'• {i}' for i in insights])}
             </div>
             """, unsafe_allow_html=True)
        
    else:
        st.info("No P&L data derived.")

def render_forecast(dfs, ai):
    st.header("Income Forecast (Beta)")
    st.markdown("""
    <div style="background-color: rgba(59, 130, 246, 0.1); padding: 12px 16px; border-radius: 8px; border-left: 4px solid #3B82F6; color: white; margin-bottom: 1rem;">
        <strong>&#128302; Forecaster:</strong> Simulating future performance based on recent average growth of Operating Income.
    </div>
    """, unsafe_allow_html=True)
    
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
        
        # AI Insights
        insights = ai.get_insights("Forecast", str(res)) if ai.model else ai.generate_fallback_insights("Forecast", res)
        with st.container():
             st.markdown(f"""
             <div style="background-color: #262730; padding: 15px; border-radius: 5px; border-left: 5px solid #AB63FA;">
                 <strong>&#129302; AI FORECAST ANALYSIS:</strong><br>
                 {'<br>'.join([f'• {i}' for i in insights])}
             </div>
             """, unsafe_allow_html=True)
             
    else:
        st.warning("Insufficient data to generate a forecast. Need at least 2 months of Operating Income data.")

def render_spending(dfs, ai):
    st.header("Spending Analysis")
    res = FinancialAnalyzer.analyze_spending(dfs)
    
    if res:
        # Summary Metrics
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

        # AI Insights
        insights = ai.get_insights("Spending", str(res['top_5_ytd'].to_dict())) if ai.model else ai.generate_fallback_insights("Spending", res)
        with st.container():
             st.markdown(f"""
             <div style="background-color: #262730; padding: 15px; border-radius: 5px; border-left: 5px solid #EF553B;">
                 <strong>&#129302; AI SPEND ANALYSIS:</strong><br>
                 {'<br>'.join([f'• {i}' for i in insights])}
             </div>
             """, unsafe_allow_html=True)
    else:
        st.info("No spending data available.")
