"""
Defines exceptions API may raise
"""


class FieldTypeError(Exception):
    def __init__(self, key: str):
        self.key = key


class FieldMissingError(Exception):
    def __init__(self, key: str):
        self.key = key
