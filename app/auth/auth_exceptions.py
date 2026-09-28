class AuthError(Exception):
    """Base exception for authentication errors."""
    pass


class InvalidCredentialsError(AuthError):
    """Raised when email/password authentication fails."""
    pass


class EmailAlreadyExistsError(AuthError):
    """Raised when an email is already registered."""
    pass


class SignupError(AuthError):
    """Raised when company signup fails."""
    pass


class DatabaseError(AuthError):
    """Raised when an authentication-related database operation fails."""
    pass




