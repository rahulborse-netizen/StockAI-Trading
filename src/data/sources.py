from typing import Dict, Any

class DataSource:
    def __init__(self, name: str, api_url: str, params: Dict[str, Any]):
        self.name = name
        self.api_url = api_url
        self.params = params

    def fetch_data(self):
        # Implement data fetching logic here
        pass

class DataSources:
    def __init__(self):
        self.sources = []

    def add_source(self, source: DataSource):
        self.sources.append(source)

    def get_sources(self):
        return self.sources

# Example of defining data sources
if __name__ == "__main__":
    data_sources = DataSources()
    
    # Add example data sources
    data_sources.add_source(DataSource("NSE", "https://api.nseindia.com", {"type": "equity"}))
    data_sources.add_source(DataSource("BSE", "https://api.bseindia.com", {"type": "equity"}))
    
    for source in data_sources.get_sources():
        print(f"Data Source: {source.name}, API URL: {source.api_url}, Params: {source.params}")