"""
Test yfinance directly to check data availability
"""
import yfinance as yf
from datetime import date, timedelta

print("Testing Yahoo Finance Data Availability")
print("="*70)

tickers = ['RELIANCE.NS', 'TCS.NS', 'INFY.NS']

# Try different date ranges
date_ranges = [
    ('2023-11-30', '2024-11-30'),
    ('2024-01-01', '2024-12-31'),
    ('2024-10-01', '2024-11-30'),
    ('2024-11-01', '2024-11-30'),
]

for ticker in tickers:
    print(f"\nTesting: {ticker}")
    print("-" * 70)
    
    for start, end in date_ranges:
        try:
            print(f"  Trying: {start} to {end}...", end=" ")
            data = yf.download(ticker, start=start, end=end, progress=False, threads=False)
            
            if data is not None and not data.empty:
                print(f"SUCCESS! Got {len(data)} rows")
                print(f"    Date range: {data.index[0]} to {data.index[-1]}")
                break
            else:
                print("No data")
        except Exception as e:
            print(f"Error: {str(e)[:50]}")

print("\n" + "="*70)
