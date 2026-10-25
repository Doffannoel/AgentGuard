class APIError(Exception):
    def __init__(self, status: int, code: str, message: str, **details):
        self.status = status
        self.code = code
        self.message = message
        self.details = details
        super().__init__(message)
