class PerchanceError(Exception):
    pass


class ConnectionError(PerchanceError):
    pass


class AuthenticationError(PerchanceError):
    pass


class RateLimitError(PerchanceError):
    pass