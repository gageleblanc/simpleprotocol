class DataLengthMismatchException(Exception):
    def __init__(self, expected: int, given: int, data: str):
        self.expected_length = expected
        self.given_length = given
        self.raw_data = data

class MalformedResponseException(Exception):
    def __init__(self, request: str):
        self.request = request