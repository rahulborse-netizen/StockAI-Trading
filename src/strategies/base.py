class BaseStrategy:
    def __init__(self):
        self.name = "Base Strategy"

    def initialize(self):
        raise NotImplementedError("Initialize method must be implemented by subclasses.")

    def execute(self, data):
        raise NotImplementedError("Execute method must be implemented by subclasses.")

    def cleanup(self):
        pass

    def get_name(self):
        return self.name