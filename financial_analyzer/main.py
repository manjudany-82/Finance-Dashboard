from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import pandas as pd
from financial_analyzer.microsoft_excel import ExcelHandler
from financial_analyzer.analysis_modes import FinancialAnalyzer

app = FastAPI(title="Financial Analyzer API", version="1.0.0")

# Models
class InsightsRequest(BaseModel):
    mode: str
    
class KPISummary(BaseModel):
    total_sales: float
    mom_sales_pct: float
    cash_balance: float
    burn_rate: float
    total_ar: float

# In-memory storage for demo purposes
# In production, this would use a database or session-based storage
data_store = {}

@app.on_event("startup")
async def startup_event():
    # Load sample data on startup
    print("Loading initial sample data...")
    data_store['sample'] = ExcelHandler.load_data(source="sample")

@app.get("/")
def read_root():
    return {"status": "online", "service": "Financial Analyzer API"}

@app.get("/api/overview", response_model=KPISummary)
def get_overview():
    dfs = data_store.get('sample')
    if not dfs:
        raise HTTPException(status_code=500, detail="Data not loaded")
    
    results = FinancialAnalyzer.analyze_overview(dfs)
    return KPISummary(
        total_sales=results.get('total_sales', 0),
        mom_sales_pct=results.get('mom_sales_pct', 0),
        cash_balance=results.get('cash_balance', 0),
        burn_rate=results.get('burn_rate', 0),
        total_ar=results.get('total_ar', 0)
    )

@app.get("/api/health")
def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
