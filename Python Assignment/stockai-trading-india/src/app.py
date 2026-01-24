from flask import Flask
from src.data.ingest import DataIngestor
from src.strategies.example_strategy import ExampleStrategy
from src.broker.zerodha_adapter import ZerodhaAdapter
from src.realtime.streamer import Streamer
from src.realtime.order_manager import OrderManager

app = Flask(__name__)

# Initialize components
data_ingestor = DataIngestor()
strategy = ExampleStrategy()
broker = ZerodhaAdapter()
streamer = Streamer()
order_manager = OrderManager()

@app.route('/')
def home():
    return "Welcome to the AI Trading Tool!"

def start_trading():
    # Main trading loop
    while True:
        market_data = data_ingestor.get_market_data()
        signals = strategy.generate_signals(market_data)
        for signal in signals:
            order_manager.execute_order(broker, signal)

if __name__ == '__main__':
    start_trading()