# Financial Analytics Dashboard

Enterprise-grade financial dashboard for analyzing QuickBooks data.

## Features
- 📊 Sales Performance Analysis
- 💰 Profitability Tracking (P&L)
- 📈 AR/AP Management
- 🔮 Revenue Forecasting
- 💸 Spending Analysis
- 🤖 AI-Powered Insights

## Deployment

This app is deployed on Streamlit Community Cloud from a **private repository**.

### Local Development
```bash
streamlit run dashboard.py
```

### Environment Variables
Set these in Streamlit Cloud Secrets:
- `GEMINI_API_KEY`: Your Google Gemini API key
- `ONEDRIVE_LINK`: Your OneDrive Excel file link

## Security
- Private GitHub repository
- Secrets managed via Streamlit Cloud
- No credentials stored in code
