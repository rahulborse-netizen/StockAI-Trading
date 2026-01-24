from websocket import create_connection
import json
import time

class Streamer:
    def __init__(self, url, on_message):
        self.url = url
        self.on_message = on_message
        self.ws = None

    def connect(self):
        self.ws = create_connection(self.url)

    def listen(self):
        while True:
            try:
                message = self.ws.recv()
                self.on_message(json.loads(message))
            except Exception as e:
                print(f"Error receiving message: {e}")
                time.sleep(1)

    def close(self):
        if self.ws:
            self.ws.close()

def on_message(data):
    # Process the incoming data
    print("Received data:", data)

if __name__ == "__main__":
    url = "wss://your-websocket-url"  # Replace with the actual WebSocket URL
    streamer = Streamer(url, on_message)
    streamer.connect()
    try:
        streamer.listen()
    except KeyboardInterrupt:
        streamer.close()