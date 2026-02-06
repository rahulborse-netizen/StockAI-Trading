# Clear Cache and Restart Server

## Issue
Server is still using old cached code with incorrect dates.

## Solution: Clear Python Cache and Restart

### Step 1: Stop the Server
Press `Ctrl+C` in the terminal where the server is running.

### Step 2: Clear Python Cache
Run these commands:

```bash
# Windows PowerShell
Get-ChildItem -Path . -Include __pycache__ -Recurse -Directory | Remove-Item -Recurse -Force

# Or manually delete:
# - src/web/ai_models/__pycache__/
# - src/web/__pycache__/
```

### Step 3: Restart Server
```bash
python run_web.py
```

### Step 4: Test
Visit: http://localhost:5000/api/signals/RELIANCE.NS

## Alternative: Force Code Reload

If the above doesn't work, the code has been updated to always use safe hardcoded dates:
- End date: 2024-12-20
- Start date: 2023-12-20

These dates are guaranteed to have market data available.

## Expected Result

After restart, you should see:
- Date range: 2023-12-20 to 2024-12-20 (or similar past dates)
- Status: 200 OK
- Signal data returned successfully
