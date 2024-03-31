"""
Defines exceptions API may raise
"""


class ClientSideError(Exception):
    def __init__(self, message: str = "Bad Request", code: int = 400):
        self.code = code
        self._message = message

    def get_message(self):
        return self._message


class FieldTypeError(ClientSideError):
    def __init__(self, key: str, message: str = "Data type error for key {0}"):
        self.key = key
        super().__init__(message.format(key))


class FieldMissingError(ClientSideError):
    def __init__(self, key: str, message: str = "Field {0} is missing"):
        self.key = key
        super().__init__(message.format(key))
