import unittest
from src.broker.zerodha_adapter import ZerodhaAdapter

class TestZerodhaAdapter(unittest.TestCase):

    def setUp(self):
        self.broker = ZerodhaAdapter(api_key='test_api_key', api_secret='test_api_secret')

    def test_place_order(self):
        order = self.broker.place_order(symbol='RELIANCE', quantity=1, order_type='BUY')
        self.assertIsNotNone(order)
        self.assertEqual(order['status'], 'success')

    def test_get_balance(self):
        balance = self.broker.get_balance()
        self.assertGreater(balance, 0)

    def test_get_positions(self):
        positions = self.broker.get_positions()
        self.assertIsInstance(positions, list)

if __name__ == '__main__':
    unittest.main()