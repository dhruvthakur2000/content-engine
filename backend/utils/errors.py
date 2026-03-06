class ContentEngineException(Exception):
    """Minimal base exception for content-engine."""
    pass

# Example custom errors (add more as needed)
class ValidationError(ContentEngineException):
    pass

class AuthorizationError(ContentEngineException):
    pass