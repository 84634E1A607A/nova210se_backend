"""
Defines exceptions API may raise
"""


class DataTypeError(Exception):
    def __init__(self, key: str):
        self.key = key
