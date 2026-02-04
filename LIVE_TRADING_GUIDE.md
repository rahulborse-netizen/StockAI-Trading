# Live Trading Guide - Important Information

## ⚠️ CRITICAL WARNINGS

**YES, you CAN use this system for live trading, BUT:**

1. **Currently NO Paper Trading Mode in Web Interface**
   - All orders placed through the web interface execute with **REAL MONEY**
   - Orders go directly to Upstox exchange
   - There is NO simulation mode in the web dashboard

2. **Manual Execution Required**
   - Trade plans require manual approval and execution
   - This is a SAFETY feature - you must review and approve each trade
   - Orders are NOT automatically executed

3. **Risk Management is Advisory**
   - Risk checks show warnings but don't prevent orders
   - You must manually review risk limits
   - Position sizing is calculated but not enforced

## ✅ Safety Features Currently in Place

1. **Manual Trade Plan Approval**
   - All trade plans start as "DRAFT"
   - You must manually approve before execution
   - You can review all details before placing orders

2. **Risk-Based Position Sizing**
   - Calculates position size based on risk parameters
   - Default: 2% risk per trade
   - Configurable in `configs/trading_config.yaml`

3. **Portfolio Risk Checks**
   - Validates position size limits
   - Checks portfolio exposure
   - Warns about over-concentration

4. **Trade Journal**
   - Tracks all executed trades
   - Links to original trade plans
   - Performance statistics

5. **Order Confirmation Required**
   - Order form must be manually filled and confirmed
   - No automatic order placement

## 🧪 Testing Before Live Trading

### Option 1: Use CLI Paper Trading (Recommended First Step)

Test your strategies with historical data:

```bash
# Paper trade a single stock
python -m src.cli paper --ticker RELIANCE.NS --start 2023-01-01 --end 2024-01-01 --outdir outputs/paper_test

# This will show you:
# - Equity curve
# - Trade blotter
# - Performance metrics
```

### Option 2: Use Trade Plan Backtesting

In the web interface:
1. Generate a trade plan
2. Click "Backtest" (if available)
3. Review expected performance before executing

### Option 3: Start with Small Positions

If you want to test live:
1. Start with minimum position sizes (1 share)
2. Use small capital allocation
3. Monitor performance closely
4. Gradually increase as you gain confidence

## 📋 Pre-Live Trading Checklist

Before using with real money:

- [ ] **Test with Paper Trading CLI** - Verify strategy performance
- [ ] **Review Risk Configuration** - Set appropriate limits in `configs/trading_config.yaml`
- [ ] **Start Small** - Begin with minimum position sizes
- [ ] **Monitor Closely** - Watch first few trades carefully
- [ ] **Understand the ML Model** - Know that it's a baseline classifier, not guaranteed
- [ ] **Set Stop Losses** - Always use stop losses in your trade plans
- [ ] **Diversify** - Don't put all capital in one trade
- [ ] **Keep Records** - Use trade journal to track performance
- [ ] **Have Exit Strategy** - Know when to stop if things go wrong

## 🔧 Recommended Configuration for Live Trading

Edit `configs/trading_config.yaml`:

```yaml
risk_management:
  max_risk_per_trade: 0.01  # 1% per trade (conservative)
  max_position_size: 0.10   # 10% max per position
  max_daily_risk: 0.03       # 3% max per day
  max_portfolio_risk: 0.20   # 20% total portfolio risk
  max_open_positions: 5      # Limit concurrent positions
```

## ⚠️ Important Limitations

1. **No Automatic Stop Loss Orders**
   - Stop losses are calculated but NOT automatically placed
   - You must manually set stop loss orders in Upstox

2. **No Automatic Position Management**
   - Positions are not automatically closed at targets
   - You must manually monitor and exit

3. **ML Model is Baseline**
   - Uses simple logistic regression
   - Not guaranteed to be profitable
   - Past performance ≠ future results

4. **Market Data Delays**
   - Uses Yahoo Finance for historical data
   - May have delays for real-time prices
   - Upstox data is real-time when connected

5. **No Guarantees**
   - Trading involves risk
   - You can lose money
   - Algorithm is a tool, not a guarantee

## 🚀 Recommended Workflow for Live Trading

1. **Week 1-2: Paper Trading**
   - Use CLI paper trading to test strategies
   - Review backtest results
   - Understand the system

2. **Week 3: Small Live Trades**
   - Start with 1-2 small positions
   - Use minimum position sizes
   - Monitor closely

3. **Week 4+: Scale Gradually**
   - Increase position sizes slowly
   - Track performance in trade journal
   - Adjust risk parameters based on results

## 💡 Best Practices

1. **Always Review Trade Plans**
   - Don't blindly execute plans
   - Verify entry/exit levels make sense
   - Check risk metrics

2. **Use Stop Losses**
   - Always set stop loss orders
   - Don't rely on mental stops
   - Protect your capital

3. **Diversify**
   - Don't put all capital in one stock
   - Spread risk across multiple positions
   - Use portfolio risk limits

4. **Monitor Performance**
   - Review trade journal regularly
   - Track win rate and profit factor
   - Adjust strategy based on results

5. **Set Limits**
   - Daily loss limits
   - Maximum position size
   - Maximum open positions

## 🔒 Security Considerations

1. **API Keys**
   - Store securely (use .env file)
   - Don't commit to git
   - Rotate periodically

2. **Session Security**
   - Use HTTPS in production
   - Set secure session cookies
   - Don't share access tokens

3. **Access Control**
   - Limit who can access the dashboard
   - Use authentication if deploying publicly

## 📞 Support & Troubleshooting

If you encounter issues:
1. Check logs in console
2. Verify Upstox connection
3. Test with small amounts first
4. Review error messages carefully

## ⚖️ Legal & Compliance

- Ensure compliance with your broker's terms
- Understand regulatory requirements
- Keep records for tax purposes
- Consult financial advisor if needed

---

**Remember: Trading involves substantial risk of loss. Only trade with money you can afford to lose. This system is a tool to assist your trading decisions, not a guarantee of profits.**
