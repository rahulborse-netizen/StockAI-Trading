class OrderManager:
    def __init__(self, broker):
        self.broker = broker
        self.open_orders = {}

    def place_order(self, symbol, quantity, order_type='market'):
        order_id = self.broker.place_order(symbol, quantity, order_type)
        self.open_orders[order_id] = {
            'symbol': symbol,
            'quantity': quantity,
            'order_type': order_type,
            'status': 'open'
        }
        return order_id

    def cancel_order(self, order_id):
        if order_id in self.open_orders:
            self.broker.cancel_order(order_id)
            self.open_orders[order_id]['status'] = 'canceled'
            return True
        return False

    def get_order_status(self, order_id):
        if order_id in self.open_orders:
            return self.open_orders[order_id]['status']
        return None

    def update_order_status(self, order_id, status):
        if order_id in self.open_orders:
            self.open_orders[order_id]['status'] = status

    def get_open_orders(self):
        return {order_id: details for order_id, details in self.open_orders.items() if details['status'] == 'open'}