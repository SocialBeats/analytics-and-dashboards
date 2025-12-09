"""
API Gateway Authentication Middleware
Trusts authentication performed by the API Gateway.
Reads user information from headers set by the Gateway.
"""

import json
from fastapi import Request, HTTPException, status
from app.core.logging import logger


# Open paths that don't require authentication (exact matches or specific prefixes)
OPEN_PATHS_EXACT = [
    "/docs",
    "/redoc",
    "/openapi.json",
    "/api/v1/kafka/health",
    "/api/v1/analytics/health",
    "/",
]


async def verify_jwt_token(request: Request, call_next):
    """
    Middleware de autenticación que confía en el API Gateway.

    El API Gateway ya validó el token JWT y agregó headers con la información del usuario:
    - x-user-id: ID del usuario
    - x-gateway-authenticated: Marca de autenticación del Gateway

    Este middleware simplemente lee esos headers y enriquece el request.state.user

    Args:
        request: FastAPI request object
        call_next: Next middleware in chain

    Returns:
        Response from next middleware

    Raises:
        HTTPException: Si la autenticación del Gateway falla
    """

    print(f"=== MIDDLEWARE DEBUG: Path: {request.url.path} ===")
    print(f"=== Headers recibidos: {dict(request.headers)} ===")

    # Skip authentication for open paths (exact match only)
    if request.url.path in OPEN_PATHS_EXACT:
        print(f"=== Skipping auth for open path: {request.url.path} ===")
        return await call_next(request)

    # Verify API version in path
    if request.url.path.startswith("/api/") and not request.url.path.startswith("/api/v"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You must specify the API version, e.g. /api/v1/...",
        )

    # Check if request comes from authenticated Gateway
    gateway_authenticated = request.headers.get("x-gateway-authenticated")
    user_id = request.headers.get("x-user-id")
    roles_header = request.headers.get("x-roles")
    user_username = request.headers.get("x-username")
    pricing_plan = request.headers.get("x-user-pricing-plan")

    # Log all headers for debugging
    logger.debug(f"All request headers: {dict(request.headers)}")
    logger.debug(
        f"Auth headers - gateway_authenticated: {gateway_authenticated}, user_id: {user_id}, roles: {roles_header}, username: {user_username}"
    )

    if not gateway_authenticated or gateway_authenticated != "true":
        logger.warn(
            f"Unauthenticated request to {request.url.path}: x-gateway-authenticated={gateway_authenticated}"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication required. Request must come through API Gateway. (x-gateway-authenticated={gateway_authenticated})",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user_id:
        logger.warn(
            f"Authenticated request to {request.url.path} missing x-user-id header. gateway_authenticated={gateway_authenticated}"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Missing user identification from Gateway. (gateway_authenticated={gateway_authenticated}, user_id={user_id})",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Parse roles from JSON string to array
    roles = []
    if roles_header:
        try:
            roles = json.loads(roles_header)
            if not isinstance(roles, list):
                roles = [roles]  # Si es un string, convertirlo a array
        except (json.JSONDecodeError, TypeError):
            # Si falla el parsing, intentar split por comas como fallback
            roles = [r.strip() for r in roles_header.split(",") if r.strip()]

    # Add user information to request state
    request.state.user = {
        "userId": user_id,
        "roles": roles,
        "username": user_username,
        "pricingPlan": pricing_plan,
    }

    logger.debug(f"User authenticated via Gateway: {user_id}")
    return await call_next(request)


async def get_current_user(request: Request) -> dict:
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
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

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

    def role_checker(request: Request) -> dict:
        # Obtener el usuario del request.state
        if not hasattr(request.state, "user"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
            )

        user = request.state.user
        # roles es un array de strings (ej: ["admin", "user"])
        user_roles = user.get("roles", [])

        # Si roles es None o string vacío, usar array vacío
        if not user_roles:
            user_roles = []

        # Verificar si el usuario tiene al menos uno de los roles permitidos
        has_permission = any(role in allowed_roles for role in user_roles)

        if not has_permission:
            logger.warn(f"Access denied for user {user.get('userId')} with roles {user_roles}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required roles: {', '.join(allowed_roles)}",
            )
        return user

    return role_checker
