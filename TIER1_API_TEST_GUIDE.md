# Tier 1 ELITE AI System - API Testing Guide

## Server Status

The web server needs to be started manually due to environment dependencies. 

## Manual Testing Steps

### Step 1: Start the Web Server

Open a terminal and run:
```bash
python run_web.py
```

Wait for the server to start. You should see:
```
============================================================
AI Trading Dashboard
============================================================
Starting web server...
Open your browser and go to: http://localhost:5000
============================================================
```

### Step 2: Test API Endpoints

Once the server is running, test these endpoints:

#### 1. ELITE Signal Generation (Main Test)
```bash
# Using curl
curl http://localhost:5000/api/signals/RELIANCE.NS

# Or visit in browser
http://localhost:5000/api/signals/RELIANCE.NS
```

**Expected Response:**
```json
{
  "ticker": "RELIANCE.NS",
  "current_price": 2450.50,
  "signal": "BUY",
  "probability": 0.65,
  "confidence": 0.75,
  "entry_level": 2445.00,
  "stop_loss": 2376.99,
  "target_1": 2523.02,
  "target_2": 2573.03,
  "recent_high": 2500.00,
  "recent_low": 2400.00,
  "volatility": 0.25,
  "model_predictions": {
    "logistic_regression": {
      "type": "logistic",
      "probability": 0.65
    }
  },
  "ensemble_method": "weighted_average",
  "model_count": 1,
  "timestamp": "2024-12-XX...",
  "elite_system": true
}
```

#### 2. Basic Signal (Fallback)
```bash
curl http://localhost:5000/api/signals/RELIANCE.NS?elite=false
```

#### 3. List All Models
```bash
curl http://localhost:5000/api/ai/models
```

**Expected Response:**
```json
{
  "models": [
    {
      "model_id": "test_logistic_v1",
      "model_type": "logistic",
      "version": "1.0",
      "feature_cols": ["ret_1", "rsi_14", "macd"],
      "performance_metrics": {
        "accuracy": 0.62,
        "sharpe_ratio": 1.8
      },
      "is_active": true,
      "prediction_count": 0
    }
  ],
  "count": 1
}
```

#### 4. Model Performance
```bash
curl http://localhost:5000/api/ai/models/test_logistic_v1/performance?days=30
```

**Expected Response:**
```json
{
  "model_id": "test_logistic_v1",
  "period_days": 30,
  "total_predictions": 5,
  "evaluated_predictions": 5,
  "accuracy": 0.6,
  "win_rate": 0.6,
  "sharpe_ratio": 1.2,
  "timestamp": "2024-12-XX..."
}
```

#### 5. Model Rankings
```bash
curl http://localhost:5000/api/ai/models/rankings?days=30
```

**Expected Response:**
```json
{
  "rankings": [
    {
      "model_id": "test_logistic_v1",
      "model_type": "logistic",
      "accuracy": 0.62,
      "win_rate": 0.6,
      "sharpe_ratio": 1.8
    }
  ],
  "period_days": 30
}
```

#### 6. Compare Models
```bash
curl "http://localhost:5000/api/ai/models/compare?models=test_logistic_v1,test_xgboost_v1&days=30"
```

## Using Python requests

You can also test using Python:

```python
import requests

BASE_URL = "http://localhost:5000"

# Test ELITE signal
response = requests.get(f"{BASE_URL}/api/signals/RELIANCE.NS")
print(response.json())

# Test model registry
response = requests.get(f"{BASE_URL}/api/ai/models")
print(response.json())
```

## Expected Behavior

### ELITE Signal Generation
- **Default**: Uses ELITE system (`elite=true` by default)
- **Advanced Features**: 50+ technical indicators
- **Multiple Models**: Logistic Regression (always), XGBoost (if available), LSTM (if available)
- **Ensemble**: Combines predictions with weighted average
- **Confidence**: Provides confidence score based on model agreement

### Fallback Behavior
- If ELITE system fails, falls back to basic Logistic Regression
- If advanced models unavailable, uses only Logistic Regression
- Always returns a valid signal

## Troubleshooting

### Server Won't Start
1. Check if port 5000 is already in use:
   ```bash
   netstat -ano | findstr :5000
   ```

2. Check for import errors:
   ```bash
   python -c "from src.web.app import app"
   ```

3. Install missing dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### API Returns Errors
- Check server logs for detailed error messages
- Verify data is available for the ticker
- Check internet connectivity (for data download)

### Models Not Available
- XGBoost and LSTM are optional
- System works with just Logistic Regression
- Install optional dependencies:
  ```bash
  pip install xgboost tensorflow
  ```

## Success Criteria

✅ **Tier 1 Complete When:**
1. Server starts without errors
2. `/api/signals/<ticker>` returns ELITE signal with `elite_system: true`
3. `/api/ai/models` returns list of registered models
4. Model performance endpoints return metrics
5. All endpoints respond within reasonable time (< 5 seconds)

## Next Steps

After confirming Tier 1 works:
- Test with multiple tickers
- Monitor model performance over time
- Proceed to Tier 2: Advanced Strategies
