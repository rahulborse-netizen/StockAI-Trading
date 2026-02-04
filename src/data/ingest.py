import requests
import pandas as pd
from datetime import datetime

class MarketDataIngestor:
    def __init__(self, source):
        self.source = source

    def fetch_data(self):
        if self.source == 'api_source':
            return self._fetch_from_api()
        elif self.source == 'csv_source':
            return self._fetch_from_csv()
        else:
            raise ValueError("Unsupported data source")

    def _fetch_from_api(self):
        # Example API endpoint (replace with actual API)
        url = "https://api.example.com/marketdata"
        response = requests.get(url)
        data = response.json()
        return pd.DataFrame(data)

    def _fetch_from_csv(self):
        # Example CSV file path (replace with actual path)
        file_path = "path/to/marketdata.csv"
        return pd.read_csv(file_path)

    def preprocess_data(self, df):
        # Convert timestamps to datetime objects
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        # Additional preprocessing steps can be added here
        return df

    def get_market_data(self):
        raw_data = self.fetch_data()
        processed_data = self.preprocess_data(raw_data)
        return processed_data

# Example usage
if __name__ == "__main__":
    ingestor = MarketDataIngestor(source='api_source')
    market_data = ingestor.get_market_data()
    print(market_data.head())