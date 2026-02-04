def calculate_moving_average(data, window_size):
    if len(data) < window_size:
        return None
    return sum(data[-window_size:]) / window_size

def calculate_rsi(data, window_size=14):
    if len(data) < window_size:
        return None
    gains = []
    losses = []
    
    for i in range(1, window_size):
        change = data[i] - data[i - 1]
        if change > 0:
            gains.append(change)
            losses.append(0)
        else:
            losses.append(-change)
            gains.append(0)

    avg_gain = sum(gains) / window_size
    avg_loss = sum(losses) / window_size

    if avg_loss == 0:
        return 100  # Avoid division by zero

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def normalize_data(data):
    min_val = min(data)
    max_val = max(data)
    return [(x - min_val) / (max_val - min_val) for x in data]

def split_data(data, train_size=0.8):
    train_length = int(len(data) * train_size)
    return data[:train_length], data[train_length:]

def get_latest_data(data, n=1):
    return data[-n:] if len(data) >= n else data
