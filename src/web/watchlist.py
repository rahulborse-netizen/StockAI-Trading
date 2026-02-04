"""
Watchlist management
"""
import json
from pathlib import Path
from typing import List

class WatchlistManager:
    """Manage watchlist of stocks to monitor"""
    
    def __init__(self, watchlist_file: Path = None):
        if watchlist_file is None:
            watchlist_file = Path('data/watchlist.json')
        self.watchlist_file = watchlist_file
        self.watchlist_file.parent.mkdir(parents=True, exist_ok=True)
        self._load_watchlist()
    
    def _load_watchlist(self):
        """Load watchlist from file"""
        if self.watchlist_file.exists():
            try:
                with open(self.watchlist_file, 'r') as f:
                    self.watchlist = json.load(f)
            except:
                self.watchlist = []
        else:
            # Default watchlist based on top performers
            self.watchlist = [
                'LT.NS',
                'HDFCBANK.NS',
                'BAJFINANCE.NS',
                'INFY.NS',
                'KOTAKBANK.NS',
                '^NSEI',
                '^NSEBANK',
            ]
            self._save_watchlist()
    
    def _save_watchlist(self):
        """Save watchlist to file"""
        with open(self.watchlist_file, 'w') as f:
            json.dump(self.watchlist, f, indent=2)
    
    def get_watchlist(self) -> List[str]:
        """Get current watchlist"""
        return self.watchlist
    
    def add_ticker(self, ticker: str):
        """Add ticker to watchlist"""
        if ticker not in self.watchlist:
            self.watchlist.append(ticker)
            self._save_watchlist()
    
    def remove_ticker(self, ticker: str):
        """Remove ticker from watchlist"""
        if ticker in self.watchlist:
            self.watchlist.remove(ticker)
            self._save_watchlist()
