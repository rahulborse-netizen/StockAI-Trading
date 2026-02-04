def create_features(data):
    # Example feature engineering function
    # This function takes raw market data and creates new features for model training
    data['SMA_10'] = data['close'].rolling(window=10).mean()  # 10-day Simple Moving Average
    data['SMA_50'] = data['close'].rolling(window=50).mean()  # 50-day Simple Moving Average
    data['EMA_20'] = data['close'].ewm(span=20, adjust=False).mean()  # 20-day Exponential Moving Average
    data['RSI'] = compute_rsi(data['close'], window=14)  # Relative Strength Index
    data['MACD'] = compute_macd(data['close'])  # Moving Average Convergence Divergence
    return data

def compute_rsi(series, window=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def compute_macd(series, short_window=12, long_window=26, signal_window=9):
    short_ema = series.ewm(span=short_window, adjust=False).mean()
    long_ema = series.ewm(span=long_window, adjust=False).mean()
    macd = short_ema - long_ema
    signal = macd.ewm(span=signal_window, adjust=False).mean()
    return macd - signal