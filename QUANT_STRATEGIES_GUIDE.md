# Quantitative Strategies Integration Guide

## 🎯 Overview

You now have **3 trading strategies** integrated into your StockAI platform:

1. **ML Strategy** (Machine Learning) - Logistic Regression with probability thresholds
2. **Mean Reversion Strategy** - Bollinger Bands + RSI
3. **Momentum Strategy** - Moving Average crossovers + MACD + ADX

Plus: **Multi-Strategy Ensemble** that combines all three!

---

## 📁 Files Created

### Strategy Implementations
- `src/web/strategies/mean_reversion_strategy.py` - Mean reversion based on Bollinger Bands
- `src/web/strategies/momentum_strategy.py` - Trend-following momentum strategy
- `src/web/strategies/strategy_manager.py` - Manages and combines multiple strategies

### API Endpoints (added to `src/web/app.py`)
- `GET /api/strategies/available` - List all strategies
- `POST /api/strategies/set_active` - Set active strategy
- `POST /api/strategies/execute` - Execute strategy and get signal
- `POST /api/strategies/compare` - Compare all strategies

---

## 🚀 How to Use

### 1. **Start Your Application**

```bash
python run_web.py
```

### 2. **Test Strategies via API**

#### **Get Available Strategies**

```bash
curl http://localhost:5000/api/strategies/available
```

**Response:**
```json
{
  "strategies": ["ml", "mean_reversion", "momentum"],
  "active_strategy": "ml",
  "details": {
    "ml": {
      "name": "ML Strategy",
      "parameters": {"prob_threshold_buy": 0.6, "prob_threshold_sell": 0.4},
      "is_active": true
    },
    "mean_reversion": {
      "name": "Mean Reversion Strategy",
      "parameters": {"ma_period": 20, "std_multiplier": 2.0},
      "is_active": false
    },
    "momentum": {
      "name": "Momentum Strategy",
      "parameters": {"short_ma_period": 10, "long_ma_period": 50},
      "is_active": false
    }
  }
}
```

#### **Execute a Strategy**

```bash
curl -X POST http://localhost:5000/api/strategies/execute \
  -H "Content-Type: application/json" \
  -d '{
    "ticker": "RELIANCE.NS",
    "strategy": "momentum"
  }'
```

**Response:**
```json
{
  "status": "success",
  "ticker": "RELIANCE.NS",
  "strategy_used": "momentum",
  "signal": "BUY",
  "confidence": 0.756,
  "entry_price": 2456.90,
  "stop_loss": 2383.19,
  "target_1": 2579.75,
  "target_2": 2702.59,
  "current_price": 2450.50,
  "metadata": {
    "strategy": "Momentum Strategy",
    "momentum_score": 0.685,
    "ma_diff_pct": 3.45,
    "macd_histogram": 12.34,
    "adx": 32.5,
    "trend_strength": "Strong"
  }
}
```

#### **Use Ensemble (All Strategies Combined)**

```bash
curl -X POST http://localhost:5000/api/strategies/execute \
  -H "Content-Type: application/json" \
  -d '{
    "ticker": "TCS.NS",
    "method": "ensemble",
    "ensemble_method": "weighted_average"
  }'
```

**Ensemble Methods:**
- `weighted_average` - Combines strategies with weights (ML: 40%, Mean Reversion: 30%, Momentum: 30%)
- `voting` - Majority vote wins
- `best_performer` - Use strategy with highest confidence

#### **Compare All Strategies**

```bash
curl -X POST http://localhost:5000/api/strategies/compare \
  -H "Content-Type: application/json" \
  -d '{"ticker": "INFY.NS"}'
```

**Response:**
```json
{
  "status": "success",
  "ticker": "INFY.NS",
  "strategies": {
    "ml": {"signal": "BUY", "confidence": 0.72, "entry_price": 1450.20},
    "mean_reversion": {"signal": "HOLD", "confidence": 0.55, "entry_price": 1448.50},
    "momentum": {"signal": "BUY", "confidence": 0.68, "entry_price": 1449.80}
  },
  "consensus": "BUY",
  "signal_counts": {"BUY": 2, "SELL": 0, "HOLD": 1}
}
```

#### **Set Active Strategy**

```bash
curl -X POST http://localhost:5000/api/strategies/set_active \
  -H "Content-Type: application/json" \
  -d '{"strategy": "momentum"}'
```

---

## 💻 Python Usage Example

### **Test Script**

```python
import requests
import json

BASE_URL = "http://localhost:5000"

def test_strategies():
    """Test all quant strategies"""
    
    # 1. Get available strategies
    print("📊 Available Strategies:")
    response = requests.get(f"{BASE_URL}/api/strategies/available")
    data = response.json()
    print(json.dumps(data, indent=2))
    print("\n" + "="*60 + "\n")
    
    # 2. Test each strategy
    tickers = ["RELIANCE.NS", "TCS.NS", "INFY.NS"]
    
    for ticker in tickers:
        print(f"🎯 Testing strategies for {ticker}")
        
        for strategy in ["ml", "mean_reversion", "momentum"]:
            response = requests.post(
                f"{BASE_URL}/api/strategies/execute",
                json={"ticker": ticker, "strategy": strategy}
            )
            result = response.json()
            
            if result.get('status') == 'success':
                print(f"  {strategy:20s}: {result['signal']:5s} (confidence: {result['confidence']:.2%})")
        
        print()
    
    # 3. Test ensemble
    print("🔥 Testing Ensemble Strategy:")
    response = requests.post(
        f"{BASE_URL}/api/strategies/execute",
        json={
            "ticker": "RELIANCE.NS",
            "method": "ensemble",
            "ensemble_method": "weighted_average"
        }
    )
    result = response.json()
    
    if result.get('status') == 'success':
        print(f"  Signal: {result['signal']}")
        print(f"  Confidence: {result['confidence']:.2%}")
        print(f"  Entry: ₹{result['entry_price']:.2f}")
        print(f"  Stop Loss: ₹{result['stop_loss']:.2f}")
        print(f"  Target 1: ₹{result['target_1']:.2f}")
        print(f"  Target 2: ₹{result['target_2']:.2f}")
        print(f"  Individual strategies: {result['metadata']['individual_strategies']}")

if __name__ == "__main__":
    test_strategies()
```

Save this as `test_strategies.py` and run:

```bash
python test_strategies.py
```

---

## 🔧 Integration with Your Dashboard

### **JavaScript Integration**

Add this to your `dashboard.js`:

```javascript
// Get strategy signal for a stock
async function getStrategySignal(ticker, strategy = 'ensemble') {
    try {
        const response = await fetch('/api/strategies/execute', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                ticker: ticker,
                method: strategy === 'ensemble' ? 'ensemble' : 'single',
                strategy: strategy === 'ensemble' ? null : strategy,
                ensemble_method: 'weighted_average'
            })
        });
        
        const result = await response.json();
        
        if (result.status === 'success') {
            return result;
        } else {
            console.error('Strategy error:', result.error);
            return null;
        }
    } catch (error) {
        console.error('Error getting strategy signal:', error);
        return null;
    }
}

// Display strategy signal on dashboard
async function displayStrategySignal(ticker) {
    const signal = await getStrategySignal(ticker, 'ensemble');
    
    if (signal) {
        const signalEl = document.getElementById('strategy-signal');
        const signalClass = signal.signal === 'BUY' ? 'text-success' : 
                           signal.signal === 'SELL' ? 'text-danger' : 'text-warning';
        
        signalEl.innerHTML = `
            <div class="strategy-signal ${signalClass}">
                <h3>${signal.signal}</h3>
                <p>Confidence: ${(signal.confidence * 100).toFixed(1)}%</p>
                <p>Entry: ₹${signal.entry_price.toFixed(2)}</p>
                <p>Target: ₹${signal.target_1.toFixed(2)} - ₹${signal.target_2.toFixed(2)}</p>
                <p>Stop Loss: ₹${signal.stop_loss.toFixed(2)}</p>
                <small>Strategy: ${signal.metadata.strategy}</small>
            </div>
        `;
    }
}

// Usage: Call when viewing a stock
displayStrategySignal('RELIANCE.NS');
```

### **Add Strategy Selector to Dashboard**

Add this HTML to your `dashboard.html`:

```html
<div class="strategy-selector">
    <label>Trading Strategy:</label>
    <select id="strategy-select" onchange="changeStrategy()">
        <option value="ensemble">📊 Ensemble (All Strategies)</option>
        <option value="ml">🤖 ML Strategy</option>
        <option value="mean_reversion">📉 Mean Reversion</option>
        <option value="momentum">📈 Momentum</option>
    </select>
</div>

<div id="strategy-signal-display">
    <!-- Strategy signals will be displayed here -->
</div>
```

---

## 📊 Strategy Comparison

### **When to Use Each Strategy**

| Strategy | Best Market Condition | Risk Level | Typical Hold Time |
|----------|----------------------|------------|-------------------|
| **ML Strategy** | Any (data-driven) | Medium | 1-5 days |
| **Mean Reversion** | Range-bound, sideways | Low-Medium | 2-7 days |
| **Momentum** | Trending (bull/bear) | Medium-High | 5-20 days |
| **Ensemble** | Any (adapts) | Medium | 3-10 days |

### **Strategy Performance Metrics**

Track these metrics for each strategy:

```python
# Add to your backtesting
metrics = {
    'sharpe_ratio': calculate_sharpe(returns),
    'max_drawdown': calculate_max_drawdown(equity_curve),
    'win_rate': winning_trades / total_trades,
    'avg_return': np.mean(returns),
    'total_return': (final_equity / initial_equity) - 1
}
```

---

## 🎓 Customization

### **Adjust Strategy Parameters**

#### **Mean Reversion**
```python
# More aggressive (tighter bands)
MeanReversionStrategy({
    'ma_period': 20,
    'std_multiplier': 1.5,  # Tighter bands
    'rsi_oversold': 35,     # Less extreme
    'rsi_overbought': 65
})

# More conservative (wider bands)
MeanReversionStrategy({
    'ma_period': 20,
    'std_multiplier': 2.5,  # Wider bands
    'rsi_oversold': 25,     # More extreme
    'rsi_overbought': 75
})
```

#### **Momentum**
```python
# Fast momentum (short-term trading)
MomentumStrategy({
    'short_ma_period': 5,
    'long_ma_period': 20,
    'momentum_period': 10,
    'min_trend_strength': 20
})

# Slow momentum (long-term trends)
MomentumStrategy({
    'short_ma_period': 20,
    'long_ma_period': 100,
    'momentum_period': 50,
    'min_trend_strength': 30
})
```

### **Adjust Ensemble Weights**

In `strategy_manager.py`, modify `_weighted_average_ensemble`:

```python
# Give more weight to ML
weights = {
    'ml': 0.5,              # 50% ML
    'mean_reversion': 0.25, # 25% Mean Reversion
    'momentum': 0.25        # 25% Momentum
}

# Or trust momentum in trending markets
weights = {
    'ml': 0.3,
    'mean_reversion': 0.2,
    'momentum': 0.5         # 50% Momentum
}
```

---

## 🧪 Backtesting Your Strategies

### **Test Strategy Performance**

```python
from src.web.strategies.strategy_manager import get_strategy_manager
from src.research.data import download_yahoo_ohlcv
from src.research.features import make_features
import pandas as pd

def backtest_strategy(ticker, strategy_name, start_date, end_date):
    """Backtest a strategy on historical data"""
    
    # Download data
    df = download_yahoo_ohlcv(ticker, start_date, end_date)
    df = make_features(df)
    
    # Initialize strategy
    manager = get_strategy_manager()
    
    # Simulate trading
    equity = 100000  # Starting capital
    position = 0
    trades = []
    
    for i in range(len(df)):
        row = df.iloc[i]
        
        # Prepare market data
        market_data = {
            'current_price': row['close'],
            'sma_10': row.get('sma_10', row['close']),
            'sma_50': row.get('sma_50', row['close']),
            'rsi_14': row.get('rsi_14', 50),
            'macd': row.get('macd', 0),
            'macd_signal': row.get('macd_signal', 0),
            # ... add more features
        }
        
        # Execute strategy
        result = manager.execute_strategy(strategy_name, market_data)
        
        # Execute trades based on signal
        if result.signal == 'BUY' and position == 0:
            position = equity / row['close']
            equity = 0
            trades.append({'date': row.name, 'action': 'BUY', 'price': row['close']})
        
        elif result.signal == 'SELL' and position > 0:
            equity = position * row['close']
            position = 0
            trades.append({'date': row.name, 'action': 'SELL', 'price': row['close']})
    
    # Calculate final equity
    if position > 0:
        equity = position * df.iloc[-1]['close']
    
    total_return = (equity / 100000 - 1) * 100
    
    print(f"Strategy: {strategy_name}")
    print(f"Total Return: {total_return:.2f}%")
    print(f"Number of Trades: {len(trades)}")
    
    return {'equity': equity, 'return': total_return, 'trades': trades}

# Test all strategies
for strategy in ['ml', 'mean_reversion', 'momentum']:
    backtest_strategy('RELIANCE.NS', strategy, '2023-01-01', '2024-01-01')
```

---

## 🚀 Next Steps

### **1. Add More Strategies**

- **Pairs Trading**: Trade correlated stocks
- **Options Strategies**: Covered calls, protective puts
- **Statistical Arbitrage**: Exploit price inefficiencies

### **2. Improve Features**

Add to `src/research/features.py`:
- ATR (Average True Range)
- ADX (Average Directional Index)
- Ichimoku Cloud
- Volume Profile

### **3. Automate Trading**

Create auto-trading module:

```python
# Auto-execute trades based on strategy signals
def auto_trade(ticker, strategy='ensemble'):
    signal = get_strategy_signal(ticker, strategy)
    
    if signal['confidence'] > 0.75:  # High confidence trades only
        if signal['signal'] == 'BUY':
            place_order(ticker, 'BUY', quantity=10)
        elif signal['signal'] == 'SELL':
            place_order(ticker, 'SELL', quantity=10)
```

### **4. Add Machine Learning Models**

- XGBoost
- Random Forest
- LSTM (Deep Learning)
- Transformer models

---

## ⚠️ Important Notes

1. **Always test in paper trading mode first!**
2. **Strategies perform differently in different market conditions**
3. **Past performance doesn't guarantee future results**
4. **Use proper risk management (stop losses, position sizing)**
5. **Monitor strategy performance regularly**

---

## 📞 Support

- Check strategy logs: Flask console output
- Test endpoint: `curl http://localhost:5000/api/strategies/available`
- Debug mode: Set `logging.DEBUG` in your logger

---

**You now have a professional-grade multi-strategy trading system!** 🎉

Start with paper trading, backtest thoroughly, then gradually scale up to live trading with proper risk management.
