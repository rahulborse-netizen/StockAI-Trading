# Paper Trading Mode - User Guide

## Overview

Paper Trading Mode allows you to test your trading strategies **without using real money**. All orders are simulated and tracked in a separate paper trading portfolio.

## Features

✅ **Safe Testing** - No real money at risk  
✅ **Realistic Simulation** - Orders execute with market prices and slippage  
✅ **Portfolio Tracking** - Track your paper trading portfolio performance  
✅ **Separate from Real Trading** - Paper positions don't mix with real positions  
✅ **Easy Toggle** - Switch between paper and live trading with one click  

## How to Use

### 1. Enable Paper Trading Mode

1. Look for the **Paper Trading** toggle switch in the top navigation bar
2. Click the toggle to turn it **ON** (green)
3. You'll see a notification: "Paper Trading Mode ENABLED"

### 2. Place Paper Orders

When Paper Trading is enabled:
- All orders you place will be **simulated** (not executed with real money)
- Orders execute immediately at simulated market prices
- You'll see "PAPER ORDER EXECUTED" in the notification
- Portfolio summary shows your paper trading cash and positions

### 3. View Paper Trading Data

**Orders Tab:**
- Shows all paper trading orders with a "Paper" badge
- Orders are marked as "EXECUTED" immediately

**Positions Tab:**
- Shows your paper trading positions
- Displays P&L and P&L% for each position
- Positions are marked with a "Paper" badge

### 4. Portfolio Summary

After placing a paper order, you'll see:
- **Cash Balance**: Remaining cash in paper trading account
- **Position Value**: Total value of open positions
- **Total Value**: Cash + Positions
- **P&L**: Total profit/loss percentage

### 5. Disable Paper Trading

1. Click the toggle to turn it **OFF**
2. You'll see a warning: "Paper Trading Mode DISABLED - Orders will use real money!"
3. All subsequent orders will be **LIVE** (real money)

## Starting Capital

- **Default**: ₹100,000
- Paper trading starts with this amount
- You can reset the portfolio anytime

## Order Execution

### Market Orders
- Execute immediately at current market price
- Includes 0.1% slippage simulation

### Limit Orders
- Execute only if price is favorable
- BUY: Executes if limit price ≤ market price
- SELL: Executes if limit price ≥ market price

### Stop Loss Orders
- Simplified execution for paper trading
- Executes at trigger price

## Important Notes

⚠️ **Paper Trading is Separate**
- Paper positions don't appear in your real Upstox account
- Paper cash balance is independent of your real account
- Switching modes doesn't affect existing positions

⚠️ **Price Updates**
- Paper positions update prices if Upstox is connected
- If not connected, prices remain at entry price

⚠️ **No Real Money**
- Paper trading uses virtual money only
- Perfect for testing strategies risk-free

## Reset Portfolio

To start fresh:
1. Contact support or use the API endpoint: `POST /api/paper-trading/reset`
2. Specify new starting capital (default: ₹100,000)

## API Endpoints

- `GET /api/paper-trading/status` - Check if paper trading is enabled
- `POST /api/paper-trading/toggle` - Enable/disable paper trading
- `GET /api/paper-trading/portfolio` - Get portfolio summary
- `GET /api/paper-trading/positions` - Get all positions
- `GET /api/paper-trading/orders` - Get all orders
- `POST /api/paper-trading/reset` - Reset portfolio

## Best Practices

1. **Test Strategies First**
   - Always test new strategies in paper trading mode
   - Verify your risk management rules work correctly

2. **Monitor Performance**
   - Track your paper trading P&L
   - Review which strategies work best

3. **Start Small in Live Trading**
   - After successful paper trading, start with small positions
   - Gradually increase as you gain confidence

4. **Use Realistic Conditions**
   - Paper trading simulates real market conditions
   - But remember: real trading has emotions and slippage

## Troubleshooting

**Toggle not working?**
- Refresh the page
- Check browser console for errors

**Orders not executing?**
- Check if you have sufficient cash (paper trading)
- Verify order parameters are correct

**Positions not updating?**
- Connect to Upstox for live price updates
- Prices update when you view positions

## Safety Features

✅ **Visual Indicators**
- Clear "Paper" badges on all paper trading data
- Toggle switch shows current mode

✅ **Confirmation Dialogs**
- Live trading requires confirmation
- Paper trading executes immediately (safe)

✅ **Separate Storage**
- Paper trading data stored separately
- Won't interfere with real trading

---

**Remember**: Paper trading is for testing only. Real trading involves risk. Always use proper risk management!
