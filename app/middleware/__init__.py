"""
Middleware package for authentication and request processing
"""

from app.middleware.authentication import verify_jwt_token

__all__ = ["verify_jwt_token"]
