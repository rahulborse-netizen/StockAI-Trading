import unittest
from src.strategies.example_strategy import ExampleStrategy

class TestExampleStrategy(unittest.TestCase):

    def setUp(self):
        self.strategy = ExampleStrategy()

    def test_initialization(self):
        self.assertIsNotNone(self.strategy)

    def test_strategy_logic(self):
        # Assuming the strategy has a method called 'execute' that returns a signal
        signal = self.strategy.execute()
        self.assertIn(signal, ['buy', 'sell', 'hold'])

    def test_parameters(self):
        # Assuming the strategy has parameters that can be set
        self.strategy.set_parameters({'param1': 10, 'param2': 5})
        self.assertEqual(self.strategy.get_parameters()['param1'], 10)
        self.assertEqual(self.strategy.get_parameters()['param2'], 5)

if __name__ == '__main__':
    unittest.main()