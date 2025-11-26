"""
JWT Authentication Middleware
Validates JWT tokens directly from Authorization header
"""

from fastapi import Request, HTTPException, status
from jose import jwt, JWTError
from app.core.config import settings
from app.core.logging import logger


# Open paths that don't require authentication
OPEN_PATHS = [
    "/docs",
    "/redoc",
    "/openapi.json",
    "/api/v1/analytics/health",
    "/",
]


async def verify_jwt_token(request: Request, call_next):
    """
    Middleware de autenticación JWT para FastAPI

    Valida tokens JWT directamente desde el header Authorization.

    Args:
        request: FastAPI request object
        call_next: Next middleware in chain

    Returns:
        Response from next middleware

    Raises:
        HTTPException: Si la autenticación falla
    """

    # Skip authentication for open paths
    if any(request.url.path.startswith(path) for path in OPEN_PATHS):
        return await call_next(request)

    # Verify API version in path
    if request.url.path.startswith("/api/") and not request.url.path.startswith("/api/v"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You must specify the API version, e.g. /api/v1/..."
        )

    # Get Authorization header
    auth_header = request.headers.get("authorization")

    if not auth_header:
        logger.warn(f"Unauthenticated request to {request.url.path}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Extract token from "Bearer <token>" format
    token_parts = auth_header.split(" ")
    if len(token_parts) != 2 or token_parts[0].lower() != "bearer":
        logger.warn(f"Invalid authorization header format for {request.url.path}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format. Use: Bearer <token>",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = token_parts[1]

    try:
        # Verify and decode JWT token
        # El algoritmo se infiere del header del token (como en JavaScript)
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            options={"verify_signature": True}
        )

        # Extract user information from token
        user_id = payload.get("userId") or payload.get("id")
        email = payload.get("email")
        role = payload.get("role", "user")

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload: missing user ID"
            )

        # Add user information to request state
        request.state.user = {
            "userId": user_id,
            "email": email,
            "role": role,
        }

        logger.debug(f"User authenticated via JWT: {user_id} ({role})")
        return await call_next(request)

    except JWTError as e:
        error_msg = str(e)
        logger.warn(f"JWT validation failed for {request.url.path}: {error_msg}")

        # Handle specific JWT errors
        if "expired" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired. Please login again.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    except Exception as e:
        logger.error(f"Authentication error for {request.url.path}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service error"
        )


def get_current_user(request: Request) -> dict:
    """
    Dependency para obtener el usuario actual de un request autenticado

    Usage en endpoints:
        @router.get("/protected")
        async def protected_endpoint(user: dict = Depends(get_current_user)):
            return {"user_id": user["userId"]}

    Args:
        request: FastAPI request object

    Returns:
        dict: User information

    Raises:
        HTTPException: Si no hay usuario autenticado
    """
    if not hasattr(request.state, "user"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )

    return request.state.user


def require_role(allowed_roles: list[str]):
    """
    Dependency factory para verificar roles de usuario

    Usage en endpoints:
        @router.get("/admin")
        async def admin_endpoint(user: dict = Depends(require_role(["admin", "moderator"]))):
            return {"message": "Admin access granted"}

    Args:
        allowed_roles: List of allowed role names

    Returns:
        Dependency function
    """
    def role_checker(user: dict = get_current_user) -> dict:
        user_role = user.get("role", "user")
        if user_role not in allowed_roles:
            logger.warn(f"Access denied for user {user.get('userId')} with role {user_role}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required roles: {', '.join(allowed_roles)}"
            )
        return user

    return role_checker
