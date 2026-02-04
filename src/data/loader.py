import pandas as pd
import numpy as np

class DataLoader:
    def __init__(self, source):
        self.source = source

    def load_historical_data(self, ticker, start_date, end_date):
        # Load historical data from the specified source
        data = self.source.get_historical_data(ticker, start_date, end_date)
        return self._process_data(data)

    def load_real_time_data(self, ticker):
        # Load real-time data from the specified source
        data = self.source.get_real_time_data(ticker)
        return self._process_data(data)

    def _process_data(self, data):
        # Process the data (e.g., handle missing values, format dates)
        df = pd.DataFrame(data)
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date')
        df = df.fillna(method='ffill')  # Forward fill to handle missing values
        return df

    def get_data_summary(self, df):
        # Get a summary of the data
        return {
            'mean': df.mean(),
            'std': df.std(),
            'min': df.min(),
            'max': df.max(),
            'count': df.count()
        }