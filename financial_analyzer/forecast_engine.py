import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from datetime import timedelta

class ForecastEngine:
    """
    Handles simple linear regression forecasting for financial metrics.
    """
    
    @staticmethod
    def forecast_series(df, date_col='Month', value_col='Revenue', months_ahead=3):
        """
        Forecasts a time series for N months ahead.
        """
        if df is None or len(df) < 3:
            return None # Not enough data
            
        # Prepare Data
        df = df.sort_values(date_col)
        df['ordinal'] = df[date_col].map(pd.Timestamp.toordinal)
        
        X = df[['ordinal']].values
        y = df[value_col].values
        
        # Fit Model
        model = LinearRegression()
        model.fit(X, y)
        
        # Future Dates
        last_date = df[date_col].max()
        future_dates = []
        future_ordinals = []
        
        for i in range(1, months_ahead + 1):
            next_date = last_date + pd.DateOffset(months=i)
            future_dates.append(next_date)
            future_ordinals.append([next_date.toordinal()])
            
        # Predict
        future_preds = model.predict(future_ordinals)
        
        future_df = pd.DataFrame({
            date_col: future_dates,
            value_col: future_preds,
            'Type': 'Forecast'
        })
        
        # Combine
        original_df = df[[date_col, value_col]].copy()
        original_df['Type'] = 'Historical'
        
        combined = pd.concat([original_df, future_df], ignore_index=True)
        
        return combined, model.coef_[0] # Return DF and Trend Slope

    @staticmethod
    def run_cash_forecast(df_cash, months_ahead=3):
        # Using daily cash balance
        if df_cash is None: return None
        
        df = df_cash[['Date', 'Balance']].copy()
        # Aggregate to weekly to reduce noise? OR just use daily
        # Let's resample to weekly for smoother regression
        df.set_index('Date', inplace=True)
        weekly = df.resample('W').last().reset_index()
        
        return ForecastEngine.forecast_series(weekly, 'Date', 'Balance', months_ahead=12) # 12 weeks ~ 3 months
